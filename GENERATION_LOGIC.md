# 中世纪奇幻城市生成器 - 生成逻辑详解

本文档详细分析了 Haxe 源代码的城市生成逻辑，解释了从 Voronoi 图到最终城市几何的完整流程。

## 目录

1. [整体架构](#整体架构)
2. [生成流程概览](#生成流程概览)
3. [详细步骤分析](#详细步骤分析)
4. [核心算法](#核心算法)
5. [数据结构](#数据结构)
6. [关键设计决策](#关键设计决策)

---

## 整体架构

### 核心类结构

```
Model (主控制器)
├── Voronoi (Voronoi 图生成)
├── Patch (城市区域)
├── CurtainWall (城墙)
├── Topology (路径查找图)
└── Ward (城市功能区)
    ├── CommonWard (通用功能区)
    ├── Market (市场)
    ├── Castle (城堡)
    ├── Cathedral (大教堂)
    └── ... (其他功能区)
```

### 数据流

```
随机种子 → Voronoi 图 → Patch 区域 → 城墙 → 街道网络 → Ward 分配 → 几何生成 → JSON 输出
```

---

## 生成流程概览

### Model.build() 主流程

```haxe
private function build():Void {
    streets = [];
    roads = [];
    
    buildPatches();        // 1. 构建 Voronoi 图和 Patch
    optimizeJunctions();   // 2. 优化顶点连接
    buildWalls();          // 3. 构建城墙
    buildStreets();         // 4. 构建街道网络
    createWards();          // 5. 分配功能区
    buildGeometry();        // 6. 生成建筑几何
}
```

### 关键决策点

在 `Model` 构造函数中，随机决定三个布尔值：
- `plazaNeeded`: 是否需要广场（Market）
- `citadelNeeded`: 是否需要城堡（Castle）
- `wallsNeeded`: 是否需要城墙

这些决策影响后续的生成流程。

---

## 详细步骤分析

### 步骤 1: buildPatches() - Voronoi 图生成

#### 1.1 生成初始点集

```haxe
var sa = Random.float() * 2 * Math.PI;  // 随机起始角度
var points = [for (i in 0...nPatches * 8) {
    var a = sa + Math.sqrt(i) * 5;      // 螺旋角度
    var r = (i == 0 ? 0 : 10 + i * (2 + Random.float()));  // 螺旋半径
    new Point(Math.cos(a) * r, Math.sin(a) * r);
}];
```

**算法特点**:
- 使用**螺旋分布**生成点，确保中心区域密度高
- 生成 `nPatches * 8` 个点（8倍冗余）
- 第一个点在原点，后续点按螺旋展开
- 半径递增：`r = 10 + i * (2 + random)`

#### 1.2 构建 Voronoi 图

```haxe
var voronoi = Voronoi.build(points);
```

**Voronoi.build() 过程**:
1. 计算点的边界框
2. 创建初始框架（4个角点）
3. 使用 Delaunay 三角剖分算法
4. 为每个点构建 Voronoi 区域

#### 1.3 松弛中心区域

```haxe
// Relaxing central wards
for (i in 0...3) {
    var toRelax = [for (j in 0...3) voronoi.points[j]];
    toRelax.push(voronoi.points[nPatches]);
    voronoi = Voronoi.relax(voronoi, toRelax);
}
```

**松弛算法** (`Voronoi.relax()`):
- 将指定点的位置移动到其 Voronoi 区域的**质心**
- 重新构建 Voronoi 图
- 重复 3 次，使中心区域更规则

**效果**: 中心区域（前 3 个点和第 nPatches 个点）变得更圆润、更规则

#### 1.4 排序和分区

```haxe
voronoi.points.sort(function(p1:Point, p2:Point)
    return MathUtils.sign(p1.length - p2.length));
var regions = voronoi.partioning();
```

- 按距离原点排序点
- 提取"真实"区域（不包含框架点）

#### 1.5 创建 Patch 并标记

```haxe
var count = 0;
for (r in regions) {
    var patch = Patch.fromRegion(r);
    patches.push(patch);
    
    if (count == 0) {
        center = patch.shape.min(function(p:Point) return p.length);
        if (plazaNeeded) plaza = patch;
    } else if (count == nPatches && citadelNeeded) {
        citadel = patch;
        citadel.withinCity = true;
    }
    
    if (count < nPatches) {
        patch.withinCity = true;
        patch.withinWalls = wallsNeeded;
        inner.push(patch);
    }
    count++;
}
```

**关键逻辑**:
- **第 0 个区域**: 中心点，可能成为 `plaza`（Market）
- **第 nPatches 个区域**: 可能成为 `citadel`（Castle）
- **前 nPatches 个区域**: 标记为 `withinCity`，加入 `inner` 列表

---

### 步骤 2: optimizeJunctions() - 顶点优化

#### 目的
移除过短的边，合并相邻顶点，简化几何形状。

#### 算法流程

```haxe
for (w in patchesToOptimize) {
    var index = 0;
    while (index < w.shape.length) {
        var v0 = w.shape[index];
        var v1 = w.shape[(index + 1) % w.shape.length];
        
        if (v0 != v1 && Point.distance(v0, v1) < 8) {
            // 1. 更新共享此顶点的其他 Patch
            for (w1 in patchByVertex(v1)) if (w1 != w) {
                w1.shape[w1.shape.indexOf(v1)] = v0;
                wards2clean.push(w1);
            }
            
            // 2. 合并顶点（中点）
            v0.addEq(v1);
            v0.scaleEq(0.5);
            
            // 3. 移除短边
            w.shape.remove(v1);
        } else {
            index++;
        }
    }
}
```

**处理逻辑**:
1. 检测短边（距离 < 8）
2. 更新共享顶点的其他 Patch
3. 将两个顶点合并为中点
4. 移除短边
5. 清理重复顶点

**效果**: 简化几何，减少不必要的细节

---

### 步骤 3: buildWalls() - 城墙构建

#### 3.1 创建边界墙

```haxe
var reserved = citadel != null ? citadel.shape.copy() : [];
border = new CurtainWall(wallsNeeded, this, inner, reserved);
```

**CurtainWall 构造函数**:
- 如果 `patches.length == 1`: 直接使用该 patch 的形状
- 否则: 使用 `Model.findCircumference()` 计算外围边界

#### 3.2 findCircumference() - 外围边界算法

```haxe
public static function findCircumference(wards:Array<Patch>):Polygon {
    var A:Array<Point> = [];
    var B:Array<Point> = [];
    
    // 1. 找出所有"外边缘"
    for (w1 in wards)
        w1.shape.forEdge(function(a, b) {
            var outerEdge = true;
            for (w2 in wards)
                if (w2.shape.findEdge(b, a) != -1) {
                    outerEdge = false;  // 找到共享边，不是外边缘
                    break;
                }
            if (outerEdge) {
                A.push(a);  // 起点
                B.push(b);  // 终点
            }
        });
    
    // 2. 构建循环路径
    var result = new Polygon();
    var index = 0;
    do {
        result.push(A[index]);
        index = A.indexOf(B[index]);  // 找到下一个点
    } while (index != 0);
    
    return result;
}
```

**算法说明**:
- **外边缘**: 只属于一个 patch 的边
- **内边缘**: 被两个 patch 共享的边
- 通过 `A.indexOf(B[index])` 连接外边缘，形成闭合多边形

#### 3.3 平滑城墙

```haxe
if (real) {
    var smoothFactor = Math.min(1, 40 / patches.length);
    shape.set([for (v in shape)
        reserved.contains(v) ? v : shape.smoothVertex(v, smoothFactor)
    ]);
}
```

- 对非保留顶点进行平滑
- 平滑因子：`min(1, 40 / patches.length)`（patch 越多，平滑越少）

#### 3.4 构建城门

```haxe
private function buildGates(real:Bool, model:Model, reserved:Array<Point>):Void {
    // 1. 找出所有可能的入口点
    var entrances:Array<Point> = if (patches.length > 1)
        shape.filter(function(v)
            return (!reserved.contains(v) && 
                    patches.count(function(p:Patch) return p.shape.contains(v)) > 1))
    else
        shape.filter(function(v) return !reserved.contains(v));
    
    // 2. 随机选择入口点作为城门
    do {
        var index = Random.int(0, entrances.length);
        var gate = entrances[index];
        gates.push(gate);
        
        // 3. 如果外部只有一个 patch，分割它以创建道路
        if (real) {
            var outerWards = model.patchByVertex(gate)
                .filter(function(w:Patch):Bool return !patches.contains(w));
            if (outerWards.length == 1) {
                var outer = outerWards[0];
                if (outer.shape.length > 3) {
                    // 找到最远的点
                    var farthest = outer.shape.max(function(v:Point)
                        if (shape.contains(v) || reserved.contains(v))
                            return Math.NEGATIVE_INFINITY;
                        else {
                            var dir = v.subtract(gate);
                            return dir.dot(out) / dir.length;
                        });
                    
                    // 分割 patch
                    var newPatches = [for (half in outer.shape.split(gate, farthest)) 
                        new Patch(half)];
                    model.patches.replace(outer, newPatches);
                }
            }
        }
        
        // 4. 移除相邻入口（避免城门太近）
        if (index == 0) {
            entrances.splice(0, 2);
            entrances.pop();
        } else if (index == entrances.length - 1) {
            entrances.splice(index - 1, 2);
            entrances.shift();
        } else
            entrances.splice(index - 1, 3);
            
    } while (entrances.length >= 3);
}
```

**城门选择逻辑**:
- **入口点**: 被多个 patch 共享的顶点（便于连接道路）
- **分割外部 patch**: 如果外部只有一个 patch，分割它以创建道路空间
- **最小间距**: 移除相邻入口，确保城门间距合理

#### 3.5 构建城堡城墙

```haxe
if (citadel != null) {
    var castle = new Castle(this, citadel);
    castle.wall.buildTowers();
    citadel.ward = castle;
    
    if (citadel.shape.compactness < 0.75)
        throw new Error("Bad citadel shape!");
    
    gates = gates.concat(castle.wall.gates);
}
```

- Castle 创建自己的 CurtainWall
- 检查紧凑度（必须 >= 0.75）
- 合并城堡的城门到总城门列表

#### 3.6 过滤远距离 Patch

```haxe
var radius = border.getRadius();
patches = patches.filter(function(p:Patch) 
    return p.shape.distance(center) < radius * 3);
```

移除距离中心超过 `radius * 3` 的 patch，减少计算量。

---

### 步骤 4: buildStreets() - 街道网络生成

#### 4.1 构建拓扑图

```haxe
topology = new Topology(this);
```

**Topology 构造函数**:
1. **创建图结构**: `Graph` 用于路径查找
2. **标记阻塞点**: citadel 和 wall 的顶点（除了 gates）
3. **遍历所有 patch**:
   - 为每个顶点创建/获取节点
   - 如果顶点不在阻塞列表中，加入 `inner` 或 `outer` 集合
   - 连接相邻顶点（边权重 = 距离）

```haxe
for (p in model.patches) {
    var withinCity = p.withinCity;
    var v1 = p.shape.last();
    var n1 = processPoint(v1);
    
    for (i in 0...p.shape.length) {
        var v0 = v1; v1 = p.shape[i];
        var n0 = n1; n1 = processPoint(v1);
        
        if (n0 != null && !border.contains(v0))
            if (withinCity) inner.add(n0) else outer.add(n0);
        if (n1 != null && !border.contains(v1))
            if (withinCity) inner.add(n1) else outer.add(n1);
        
        if (n0 != null && n1 != null)
            n0.link(n1, Point.distance(v0, v1));
    }
}
```

#### 4.2 构建街道路径

```haxe
for (gate in gates) {
    // 每个城门连接到最近的 plaza 角点或中心点
    var end:Point = plaza != null ?
        plaza.shape.min(function(v) return Point.distance(v, gate)) :
        center;
    
    // 使用 A* 算法查找路径
    var street = topology.buildPath(gate, end, topology.outer);
    if (street != null) {
        streets.push(street);
        
        // 如果是边界城门，还要构建外部道路
        if (border.gates.contains(gate)) {
            var dir = gate.norm(1000);  // 城门方向延伸
            var start = null;
            var dist = Math.POSITIVE_INFINITY;
            // 找到最接近延伸方向的节点
            for (p in topology.node2pt) {
                var d = Point.distance(p, dir);
                if (d < dist) {
                    dist = d;
                    start = p;
                }
            }
            
            var road = topology.buildPath(start, gate, topology.inner);
            if (road != null) roads.push(road);
        }
    } else
        throw new Error("Unable to build a street!");
}
```

**路径查找逻辑**:
- **街道 (streets)**: 从城门到 plaza/中心，使用 `outer` 节点集合
- **道路 (roads)**: 从外部到边界城门，使用 `inner` 节点集合
- **A* 算法**: `graph.aStar(start, goal, exclude)`

#### 4.3 整理道路网络 (tidyUpRoads)

```haxe
private function tidyUpRoads() {
    var segments = new Array<Segment>();
    
    // 1. 将街道和道路切割成线段
    function cut2segments(street:Street) {
        var v0:Point = null;
        var v1:Point = street[0];
        for (i in 1...street.length) {
            v0 = v1;
            v1 = street[i];
            
            // 跳过 plaza 内的线段
            if (plaza != null && plaza.shape.contains(v0) && plaza.shape.contains(v1))
                continue;
            
            // 检查线段是否已存在
            var exists = false;
            for (seg in segments)
                if (seg.start == v0 && seg.end == v1) {
                    exists = true;
                    break;
                }
            
            if (!exists)
                segments.push(new Segment(v0, v1));
        }
    }
    
    // 2. 将线段连接成连续路径
    arteries = [];
    while (segments.length > 0) {
        var seg = segments.pop();
        var attached = false;
        
        for (a in arteries)
            if (a[0] == seg.end) {
                a.unshift(seg.start);  // 连接到开头
                attached = true;
                break;
            } else if (a.last() == seg.start) {
                a.push(seg.end);  // 连接到结尾
                attached = true;
                break;
            }
        
        if (!attached)
            arteries.push([seg.start, seg.end]);
    }
}
```

**目的**:
- 去除重复线段
- 将线段连接成连续路径
- 创建 `arteries`（动脉网络）

#### 4.4 平滑街道

```haxe
function smoothStreet(street:Street):Void {
    var smoothed = street.smoothVertexEq(3);
    for (i in 1...street.length-1)
        street[i].set(smoothed[i]);
}

for (a in arteries)
    smoothStreet(a);
```

使用 `smoothVertexEq(3)` 平滑街道顶点（保留首尾）。

---

### 步骤 5: createWards() - 功能区分配

#### 5.1 预分配特殊区域

```haxe
var unassigned = inner.copy();

// 1. 分配 Market (plaza)
if (plaza != null) {
    plaza.ward = new Market(this, plaza);
    unassigned.remove(plaza);
}

// 2. 分配 GateWard (城门区域)
for (gate in border.gates)
    for (patch in patchByVertex(gate))
        if (patch.withinCity && patch.ward == null && 
            Random.bool(wall == null ? 0.2 : 0.5)) {
            patch.ward = new GateWard(this, patch);
            unassigned.remove(patch);
        }
```

#### 5.2 Ward 类型列表

```haxe
public static var WARDS:Array<Class<Ward>> = [
    CraftsmenWard, CraftsmenWard, MerchantWard, CraftsmenWard, CraftsmenWard, Cathedral,
    CraftsmenWard, CraftsmenWard, CraftsmenWard, CraftsmenWard, CraftsmenWard,
    CraftsmenWard, CraftsmenWard, CraftsmenWard, AdministrationWard, CraftsmenWard,
    Slum, CraftsmenWard, Slum, PatriciateWard, Market,
    Slum, CraftsmenWard, CraftsmenWard, CraftsmenWard, Slum,
    CraftsmenWard, CraftsmenWard, CraftsmenWard, MilitaryWard, Slum,
    CraftsmenWard, Park, PatriciateWard, Market, MerchantWard
];
```

**分布特点**:
- **CraftsmenWard**: 最多（约 60%）
- **Slum**: 约 15%
- **其他**: Market, Cathedral, AdministrationWard, PatriciateWard, MilitaryWard, Park, MerchantWard

#### 5.3 随机打乱

```haxe
var wards = WARDS.copy();
// some shuffling
for (i in 0...Std.int(wards.length / 10)) {
    var index = Random.int(0, (wards.length - 1));
    var tmp = wards[index];
    wards[index] = wards[index + 1];
    wards[index+1] = tmp;
}
```

轻微打乱列表（交换约 10% 的元素对）。

#### 5.4 智能分配

```haxe
while (unassigned.length > 0) {
    var bestPatch:Patch = null;
    
    var wardClass = wards.length > 0 ? wards.shift() : Slum;
    var rateFunc = Reflect.field(wardClass, "rateLocation");
    
    if (rateFunc == null)
        // 没有评分函数，随机选择
        do bestPatch = unassigned.random()
        while (bestPatch.ward != null);
    else
        // 使用评分函数选择最佳位置
        bestPatch = unassigned.min(function(patch:Patch) {
            return patch.ward == null ? 
                Reflect.callMethod(wardClass, rateFunc, [this, patch]) : 
                Math.POSITIVE_INFINITY;
        });
    
    bestPatch.ward = Type.createInstance(wardClass, [this, bestPatch]);
    unassigned.remove(bestPatch);
}
```

**分配策略**:
- **有 `rateLocation()`**: 选择评分最低的 patch（评分越低越好）
- **无 `rateLocation()`**: 随机选择

**评分函数示例**:
- `Slum.rateLocation()`: `-distance(center)`（远离中心）
- `MerchantWard.rateLocation()`: `distance(center)`（靠近中心）
- `MilitaryWard.rateLocation()`: 优先 citadel 或 wall 相邻
- `PatriciateWard.rateLocation()`: 偏好 Park 相邻，避免 Slum 相邻

#### 5.5 郊区处理

```haxe
// Outskirts
if (wall != null)
    for (gate in wall.gates) 
        if (!Random.bool(1 / (nPatches - 5))) {
            for (patch in patchByVertex(gate))
                if (patch.ward == null) {
                    patch.withinCity = true;
                    patch.ward = new GateWard(this, patch);
                }
        }

// 计算城市半径和处理乡村
cityRadius = 0;
for (patch in patches)
    if (patch.withinCity)
        for (v in patch.shape)
            cityRadius = Math.max(cityRadius, v.length);
    else if (patch.ward == null)
        patch.ward = Random.bool(0.2) && patch.shape.compactness >= 0.7 ?
            new Farm(this, patch) :
            new Ward(this, patch);
```

- 城门附近可能分配 GateWard
- 计算城市半径（最远顶点距离）
- 未分配的 patch：20% 概率成为 Farm（如果紧凑度 >= 0.7），否则为普通 Ward

---

### 步骤 6: buildGeometry() - 几何生成

```haxe
private function buildGeometry()
    for (patch in patches)
        patch.ward.createGeometry();
```

每个 Ward 类型有自己的 `createGeometry()` 实现：

#### 6.1 CommonWard.createGeometry()

```haxe
override public function createGeometry() {
    var block = getCityBlock();
    geometry = Ward.createAlleys(block, minSq, gridChaos, sizeChaos, emptyProb);
    
    if (!model.isEnclosed(patch))
        filterOutskirts();
}
```

**流程**:
1. **getCityBlock()**: 根据街道位置内缩 patch
2. **createAlleys()**: 递归二分创建建筑
3. **filterOutskirts()**: 如果不在城墙内，过滤边缘建筑

#### 6.2 getCityBlock() - 城市街区计算

```haxe
public function getCityBlock():Polygon {
    var insetDist:Array<Float> = [];
    var innerPatch = model.wall == null || patch.withinWalls;
    
    patch.shape.forEdge(function(v0, v1) {
        if (model.wall != null && model.wall.bordersBy(patch, v0, v1))
            insetDist.push(MAIN_STREET/2);
        else {
            var onStreet = innerPatch && (
                model.plaza != null && model.plaza.shape.findEdge(v1, v0) != -1
            );
            if (!onStreet)
                for (street in model.arteries)
                    if (street.contains(v0) && street.contains(v1)) {
                        onStreet = true;
                        break;
                    }
            insetDist.push(
                (onStreet ? MAIN_STREET : (innerPatch ? REGULAR_STREET : ALLEY)) / 2
            );
        }
    });
    
    return patch.shape.isConvex() ?
        patch.shape.shrink(insetDist) :
        patch.shape.buffer(insetDist);
}
```

**内缩距离**:
- **城墙边**: `MAIN_STREET/2` (1.0)
- **主街道**: `MAIN_STREET/2` (1.0)
- **普通街道**: `REGULAR_STREET/2` (0.5)
- **小巷**: `ALLEY/2` (0.3)

#### 6.3 createAlleys() - 递归二分算法

```haxe
public static function createAlleys(
    p:Polygon, minSq:Float, gridChaos:Float, 
    sizeChaos:Float, emptyProb:Float=0.04, split=true
):Array<Polygon> {
    // 1. 找到最长边
    var v:Point = null;
    var length = -1.0;
    p.forEdge(function(p0, p1) {
        var len = Point.distance(p0, p1);
        if (len > length) {
            length = len;
            v = p0;
        }
    });
    
    // 2. 计算分割比例和角度
    var spread = 0.8 * gridChaos;
    var ratio = (1 - spread) / 2 + Random.float() * spread;
    var angleSpread = Math.PI / 6 * gridChaos * (p.square < minSq * 4 ? 0.0 : 1);
    var b = (Random.float() - 0.5) * angleSpread;
    
    // 3. 二分多边形
    var halves = Cutter.bisect(p, v, ratio, b, split ? ALLEY : 0.0);
    
    // 4. 递归处理
    var buildings = [];
    for (half in halves) {
        if (half.square < minSq * Math.pow(2, 4 * sizeChaos * (Random.float() - 0.5))) {
            if (!Random.bool(emptyProb))
                buildings.push(half);
        } else {
            buildings = buildings.concat(
                createAlleys(half, minSq, gridChaos, sizeChaos, emptyProb, 
                    half.square > minSq / (Random.float() * Random.float()))
            );
        }
    }
    
    return buildings;
}
```

**算法特点**:
- **最长边分割**: 总是沿最长边分割
- **随机比例**: `ratio = (1-spread)/2 + random*spread`
- **角度扰动**: `angleSpread` 控制网格混乱度
- **递归终止**: 面积小于阈值时停止
- **空概率**: `emptyProb` 控制空地比例

#### 6.4 filterOutskirts() - 郊区过滤

```haxe
private function filterOutskirts() {
    var populatedEdges:Array<Dynamic> = [];
    
    // 1. 标记人口密集的边缘
    patch.shape.forEdge(function(v1:Point, v2:Point) {
        var onRoad = false;
        for (street in model.arteries)
            if (street.contains(v1) && street.contains(v2)) {
                onRoad = true;
                break;
            }
        
        if (onRoad)
            addEdge(v1, v2, 1);
        else {
            var n = model.getNeighbour(patch, v1);
            if (n != null && n.withinCity)
                addEdge(v1, v2, model.isEnclosed(n) ? 1 : 0.4);
        }
    });
    
    // 2. 计算顶点密度
    var density = [for (v in patch.shape)
        if (model.gates.contains(v)) 1 else
            model.patchByVertex(v).every(function(p:Patch) return p.withinCity) ? 
                2 * Random.float() : 0
    ];
    
    // 3. 过滤建筑
    geometry = geometry.filter(function(building:Polygon) {
        var minDist = 1.0;
        // 计算到边缘的最小距离
        for (edge in populatedEdges)
            for (v in building) {
                var d = GeomUtils.distance2line(edge.x, edge.y, edge.dx, edge.dy, v.x, v.y);
                var dist = d / edge.d;
                if (dist < minDist) minDist = dist;
            }
        
        // 计算密度权重
        var c = building.center;
        var i = patch.shape.interpolate(c);
        var p = 0.0;
        for (j in 0...i.length)
            p += density[j] * i[j];
        minDist /= p;
        
        // 随机过滤
        return Random.fuzzy(1) > minDist;
    });
}
```

**过滤逻辑**:
- **边缘权重**: 道路边 = 1.0，城市邻居 = 1.0，郊区邻居 = 0.4
- **密度计算**: 基于顶点周围的城市化程度
- **距离阈值**: 建筑到边缘的距离 / 密度权重
- **随机性**: 使用 `Random.fuzzy()` 增加随机性

---

## 核心算法

### 1. Voronoi 图生成 (Delaunay 三角剖分)

**算法**: 增量式 Delaunay 三角剖分

1. 创建初始框架（4个角点，2个三角形）
2. 对每个点：
   - 找到包含该点的三角形
   - 分割三角形
   - 翻转边以保持 Delaunay 性质
3. 构建 Voronoi 区域（三角形外心）

**复杂度**: O(n log n)

### 2. A* 路径查找

```haxe
public function aStar(start:Node, goal:Node, exclude:Array<Node>=null):Array<Node> {
    var closedSet = exclude != null ? exclude.copy() : [];
    var openSet = [start];
    var cameFrom = new Map<Node, Node>();
    var gScore = [start => 0];
    
    while (openSet.length > 0) {
        var current = openSet.shift();
        if (current == goal)
            return buildPath(cameFrom, current);
        
        openSet.remove(current);
        closedSet.push(current);
        
        var curScore = gScore.get(current);
        for (neighbour in current.links.keys()) {
            if (closedSet.contains(neighbour)) continue;
            
            var score = curScore + current.links.get(neighbour);
            if (!openSet.contains(neighbour))
                openSet.push(neighbour);
            else if (score >= gScore.get(neighbour))
                continue;
            
            cameFrom.set(neighbour, current);
            gScore.set(neighbour, score);
        }
    }
    
    return null;
}
```

**特点**: 使用边权重（距离）作为代价，无启发式函数（Dijkstra 变种）

### 3. 外围边界查找 (findCircumference)

**算法**: 边追踪

1. 找出所有外边缘（只属于一个 patch）
2. 构建边列表 (A: 起点, B: 终点)
3. 从 A[0] 开始，找到 B[0] 在 A 中的位置
4. 重复直到回到起点

**关键**: `index = A.indexOf(B[index])` 连接边

### 4. 多边形平滑 (smoothVertexEq)

```haxe
public function smoothVertexEq(f=1.0):Polygon {
    var len = this.length;
    var v1 = this[len-1];
    var v2 = this[0];
    return [for (i in 0...len) {
        var v0 = v1; v1 = v2; v2 = this[(i + 1) % len];
        new Point(
            (v0.x + v1.x * f + v2.x) / (2 + f),
            (v0.y + v1.y * f + v2.y) / (2 + f)
        );
    }];
}
```

**公式**: `v_new = (v_prev + v_current * f + v_next) / (2 + f)`

- `f = 1.0`: 平均平滑
- `f = 3.0`: 更强平滑（用于街道）

---

## 数据结构

### Patch
```haxe
class Patch {
    public var shape:Polygon;      // 多边形形状
    public var ward:Ward;          // 功能区类型
    public var withinWalls:Bool;  // 是否在城墙内
    public var withinCity:Bool;   // 是否在城市内
}
```

### CurtainWall
```haxe
class CurtainWall {
    public var shape:Polygon;      // 城墙形状
    public var segments:Array<Bool>; // 段是否有效
    public var gates:Array<Point>;  // 城门列表
    public var towers:Array<Point>; // 塔楼列表
}
```

### Topology
```haxe
class Topology {
    private var graph:Graph;              // 图结构
    public var pt2node:Map<Point, Node>;  // 点→节点映射
    public var node2pt:Map<Node, Point>;  // 节点→点映射
    public var inner:Array<Node>;         // 城市内节点
    public var outer:Array<Node>;         // 城市外节点
}
```

### Ward
```haxe
class Ward {
    public var model:Model;
    public var patch:Patch;
    public var geometry:Array<Polygon>;  // 建筑几何列表
}
```

---

## 关键设计决策

### 1. 螺旋点分布
- **原因**: 确保中心区域密度高，边缘稀疏
- **效果**: 自然形成城市中心→郊区的梯度

### 2. Voronoi 松弛
- **原因**: 中心区域需要更规则的形状（适合 plaza）
- **效果**: 中心区域更圆润，边缘保持自然

### 3. 顶点优化
- **原因**: 移除过短边，简化几何
- **效果**: 减少不必要的细节，提高性能

### 4. 智能 Ward 分配
- **原因**: 不同类型 Ward 有位置偏好
- **效果**: 更真实的城市布局（如 Slum 在边缘，Merchant 在中心）

### 5. 递归二分建筑生成
- **原因**: 创建有机的建筑布局
- **效果**: 避免完全规整的网格，增加自然感

### 6. 郊区过滤
- **原因**: 郊区建筑密度应低于城市内
- **效果**: 创建城市→郊区的过渡

---

## 随机性控制

### 确定性随机数生成器

```haxe
class Random {
    private static inline var g = 48271.0;
    private static inline var n = 2147483647;
    private static var seed = 1;
    
    private static inline function next():Int
        return (seed = Std.int((seed * g) % n));
    
    public static inline function float():Float
        return next() / n;
}
```

**特点**:
- 线性同余生成器 (LCG)
- 给定种子，生成序列确定
- 支持 `reset(seed)` 重置

### 关键随机决策

1. **初始角度**: `sa = Random.float() * 2π`
2. **点半径**: `r = 10 + i * (2 + Random.float())`
3. **Ward 分配**: 随机打乱 + 智能选择
4. **建筑生成**: 递归分割的随机比例和角度
5. **空概率**: `emptyProb` 控制空地

---

## 性能优化

### 1. Patch 过滤
```haxe
patches = patches.filter(function(p:Patch) 
    return p.shape.distance(center) < radius * 3);
```
移除远距离 patch，减少后续计算量。

### 2. 图结构缓存
Topology 预先构建图，避免重复计算。

### 3. 递归深度限制
`createAlleys()` 有隐式深度限制（面积阈值）。

---

## 错误处理

### 重试机制
```haxe
do try {
    build();
    instance = this;
} catch (e:Error) {
    trace(e.message);
    instance = null;
} while (instance == null);
```

如果生成失败（如 "Bad citadel shape!"），会重试（最多 10 次）。

### 常见错误
1. **"Bad walled area shape!"**: 无法找到入口点
2. **"Unable to build a street!"**: A* 无法找到路径
3. **"Bad citadel shape!"**: citadel 紧凑度 < 0.75

---

## 特殊 Ward 类型的几何生成

### Market (市场)

```haxe
override public function createGeometry() {
    var statue = Random.bool(0.6);  // 60% 概率是雕像
    var offset = statue || Random.bool(0.3);  // 雕像总是偏移，喷泉30%偏移
    
    // 找到最长边（用于旋转和偏移）
    var v0:Point = null;
    var v1:Point = null;
    if (statue || offset) {
        var length = -1.0;
        patch.shape.forEdge(function(p0, p1) {
            var len = Point.distance(p0, p1);
            if (len > length) {
                length = len;
                v0 = p0;
                v1 = p1;
            }
        });
    }
    
    // 创建对象
    var object:Polygon;
    if (statue) {
        object = Polygon.rect(1 + Random.float(), 1 + Random.float());
        object.rotate(Math.atan2(v1.y - v0.y, v1.x - v0.x));  // 沿边旋转
    } else {
        object = Polygon.circle(1 + Random.float());  // 喷泉
    }
    
    // 偏移位置
    if (offset) {
        var gravity = GeomUtils.interpolate(v0, v1);  // 边的中点
        object.offset(GeomUtils.interpolate(patch.shape.centroid, gravity, 
            0.2 + Random.float() * 0.4));
    } else {
        object.offset(patch.shape.centroid);  // 中心
    }
    
    geometry = [object];
}
```

**特点**:
- 雕像：矩形，沿最长边旋转
- 喷泉：圆形
- 位置：可能偏移到边的中点方向

### Castle (城堡)

```haxe
override public function createGeometry() {
    var block = patch.shape.shrinkEq(Ward.MAIN_STREET * 2);  // 内缩 4.0
    geometry = Ward.createOrthoBuilding(block, 
        Math.sqrt(block.square) * 4, 0.6);
}
```

**特点**:
- 大幅内缩（4.0 单位）
- 使用正交建筑算法（矩形建筑）

### Cathedral (大教堂)

```haxe
override public function createGeometry()
    geometry = Random.bool(0.4) ?
        Cutter.ring(getCityBlock(), 2 + Random.float() * 4) :
        Ward.createOrthoBuilding(getCityBlock(), 50, 0.8);
```

**特点**:
- 40% 概率：环形结构（`Cutter.ring()`）
- 60% 概率：正交建筑

### Park (公园)

```haxe
override public function createGeometry() {
    var block = getCityBlock();
    geometry = block.compactness >= 0.7 ?
        Cutter.radial(block, null, Ward.ALLEY) :
        Cutter.semiRadial(block, null, Ward.ALLEY);
}
```

**特点**:
- 紧凑度 >= 0.7：径向切割（从中心辐射）
- 否则：半径向切割（从最近顶点辐射）

### Farm (农场)

```haxe
override public function createGeometry() {
    var housing = Polygon.rect(4, 4);  // 4x4 房屋
    var pos = GeomUtils.interpolate(
        patch.shape.random(),           // 随机顶点
        patch.shape.centroid,           // 质心
        0.3 + Random.float() * 0.4      // 30%-70% 之间
    );
    housing.rotate(Random.float() * Math.PI);  // 随机旋转
    housing.offset(pos);
    
    geometry = Ward.createOrthoBuilding(housing, 8, 0.5);
}
```

**特点**:
- 单个 4x4 房屋
- 位置在随机顶点和质心之间
- 随机旋转
- 使用正交建筑算法扩展

---

## Cutter 工具类

### bisect() - 二分切割

```haxe
public static function bisect(
    poly:Polygon, vertex:Point, ratio=0.5, angle=0.0, gap=0.0
):Array<Polygon> {
    var next = poly.next(vertex);
    var p1 = GeomUtils.interpolate(vertex, next, ratio);
    var d = next.subtract(vertex);
    
    // 旋转向量
    var cosB = Math.cos(angle);
    var sinB = Math.sin(angle);
    var vx = d.x * cosB - d.y * sinB;
    var vy = d.y * cosB + d.x * sinB;
    var p2 = new Point(p1.x - vy, p1.y + vx);
    
    return poly.cut(p1, p2, gap);
}
```

**算法**:
1. 在边上按 `ratio` 找到点 `p1`
2. 计算垂直方向（旋转 `angle`）
3. 创建切割线 `p1 → p2`
4. 使用 `poly.cut()` 分割多边形

### radial() - 径向切割

```haxe
public static function radial(
    poly:Polygon, center:Point=null, gap=0.0
):Array<Polygon> {
    if (center == null)
        center = poly.centroid;
    
    var sectors:Array<Polygon> = [];
    poly.forEdge(function(v0, v1) {
        var sector = new Polygon([center, v0, v1]);
        if (gap > 0)
            sector = sector.shrink([gap/2, 0, gap/2]);
        sectors.push(sector);
    });
    return sectors;
}
```

**效果**: 从中心点辐射到每条边，创建扇形区域

### semiRadial() - 半径向切割

```haxe
public static function semiRadial(
    poly:Polygon, center:Point=null, gap=0.0
):Array<Polygon> {
    if (center == null) {
        var centroid = poly.centroid;
        center = poly.min(function(v:Point) 
            return Point.distance(v, centroid));
    }
    
    gap /= 2;
    var sectors:Array<Polygon> = [];
    poly.forEdge(function(v0, v1)
        if (v0 != center && v1 != center) {
            var sector = new Polygon([center, v0, v1]);
            if (gap > 0) {
                var d = [
                    poly.findEdge(center, v0) == -1 ? gap : 0,
                    0,
                    poly.findEdge(v1, center) == -1 ? gap : 0
                ];
                sector = sector.shrink(d);
            }
            sectors.push(sector);
        }
    );
    return sectors;
}
```

**效果**: 从最近顶点辐射，跳过包含该顶点的边

### ring() - 环形切割

```haxe
public static function ring(poly:Polygon, thickness:Float):Array<Polygon> {
    var slices:Array<Dynamic> = [];
    poly.forEdge(function(v1:Point, v2:Point) {
        var v = v2.subtract(v1);
        var n = v.rotate90().norm(thickness);
        slices.push({p1:v1.add(n), p2:v2.add(n), len:v.length});
    });
    
    // 按长度排序（短边优先）
    slices.sort(function(s1, s2) return (s1.len - s2.len));
    
    var peel:Array<Polygon> = [];
    var p = poly;
    for (i in 0...slices.length) {
        var halves = p.cut(slices[i].p1, slices[i].p2);
        p = halves[0];  // 保留内部
        if (halves.length == 2)
            peel.push(halves[1]);  // 收集外部环
    }
    
    return peel;
}
```

**算法**:
1. 为每条边创建偏移线（向外 `thickness` 距离）
2. 按边长度排序（短边优先切割）
3. 依次切割，收集外部环
4. 返回所有环片段

**用途**: 创建大教堂的环形结构

### createOrthoBuilding() - 正交建筑生成

```haxe
public static function createOrthoBuilding(
    poly:Polygon, minBlockSq:Float, fill:Float
):Array<Polygon> {
    function slice(poly:Polygon, c1:Point, c2:Point):Array<Polygon> {
        // 1. 找到最长边
        var v0 = findLongestEdge(poly);
        var v1 = poly.next(v0);
        var v = v1.subtract(v0);
        
        // 2. 在边上选择分割点
        var ratio = 0.4 + Random.float() * 0.2;  // 40%-60%
        var p1 = GeomUtils.interpolate(v0, v1, ratio);
        
        // 3. 选择切割方向（c1 或 c2）
        var c:Point = if (Math.abs(GeomUtils.scalar(v.x, v.y, c1.x, c1.y)) < 
                          Math.abs(GeomUtils.scalar(v.x, v.y, c2.x, c2.y)))
            c1 else c2;
        
        // 4. 切割多边形
        var halves = poly.cut(p1, p1.add(c));
        var buildings = [];
        for (half in halves) {
            if (half.square < minBlockSq * Math.pow(2, Random.normal() * 2 - 1)) {
                if (Random.bool(fill))
                    buildings.push(half);
            } else {
                buildings = buildings.concat(slice(half, c1, c2));
            }
        }
        return buildings;
    }
    
    if (poly.square < minBlockSq) {
        return [poly];
    } else {
        // 初始化两个正交方向
        var c1 = poly.vector(findLongestEdge(poly));  // 最长边方向
        var c2 = c1.rotate90();  // 垂直方向
        
        // 循环直到成功生成建筑
        while (true) {
            var blocks = slice(poly, c1, c2);
            if (blocks.length > 0)
                return blocks;
        }
    }
}
```

**算法说明**:
1. **初始化方向**: `c1` = 最长边方向，`c2` = 垂直方向
2. **递归分割**: 沿最长边分割，选择更接近垂直的方向
3. **终止条件**: 面积 < `minBlockSq * random_factor`
4. **填充概率**: `fill` 参数控制是否保留小块
5. **重试机制**: 如果分割失败（`blocks.length == 0`），重试

**特点**:
- 创建矩形/近似矩形的建筑
- 保持正交性（垂直切割）
- 用于 Castle、Cathedral 等正式建筑

---

## 总结

城市生成器使用以下核心思想：

1. **Voronoi 图**: 创建自然的分区
2. **智能分配**: Ward 类型根据位置偏好分配
3. **路径查找**: A* 算法连接城门和中心
4. **递归几何**: 二分算法创建有机建筑布局
5. **随机性**: LCG 确保可重复性
6. **多样化几何**: 不同 Ward 类型使用不同的几何生成策略

整个流程从简单的点集开始，通过一系列几何操作和智能决策，最终生成一个完整的中世纪奇幻城市。

### 关键创新点

1. **螺旋点分布**: 自然形成中心→边缘的密度梯度
2. **Voronoi 松弛**: 优化中心区域的形状
3. **智能 Ward 分配**: 基于位置评分的分配系统
4. **递归二分**: 创建有机而非规整的建筑布局
5. **郊区过滤**: 模拟城市边缘的建筑密度衰减

### 算法复杂度

- **Voronoi 生成**: O(n log n)
- **路径查找**: O(E + V log V) (A*)
- **几何生成**: O(m) (m = 建筑数量，递归深度有限)
- **总体**: 对于 n=40 (Metropolis)，生成时间 < 1 秒

### 可扩展性

- **Ward 类型**: 易于添加新的 Ward 类
- **几何算法**: Cutter 类提供多种切割方法
- **评分系统**: `rateLocation()` 方法可自定义位置偏好
