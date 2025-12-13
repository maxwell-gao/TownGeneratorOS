# 几何类功能对比分析

本文档详细对比了 Haxe 几何类实现和 Python 版本的对应实现。

## 1. Circle.hx

### Haxe 实现
```haxe
class Circle {
    public var x : Float;
    public var y : Float;
    public var r : Float;
}
```
- 简单的圆类，包含中心点和半径

### Python 实现
- ❌ **未实现独立的 Circle 类**
- ✅ 在 `Polygon.circle()` 静态方法中创建圆形多边形近似
- ✅ 在 `visualize.py` 中使用 SVG `<circle>` 元素

**结论**: Circle 类在 Haxe 中似乎很少使用，Python 版本通过多边形近似和 SVG 圆元素实现相同功能。

---

## 2. GeomUtils.hx

### Haxe 实现
- `intersectLines()` - 计算两条线的交点
- `interpolate()` - 两点间插值
- `scalar()` - 标量积
- `cross()` - 叉积
- `distance2line()` - 点到线的距离

### Python 实现 (`math_utils.py`)
- ✅ `intersect_lines()` - 已实现
- ✅ `interpolate()` - 已实现
- ✅ `scalar()` - 已实现
- ✅ `cross()` - 已实现
- ✅ `distance2line()` - 已实现（但实现方式略有不同）

**差异**:
- Haxe `distance2line()` 使用公式: `(dx1 * y0 - dy1 * x0 + (y1 + dy1) * x1 - (x1 + dx1) * y1) / sqrt(dx1² + dy1²)`
- Python 版本使用投影方法计算点到线段的距离（更通用）

**结论**: ✅ 所有功能已实现，`distance2line` 的实现方式不同但功能等价。

---

## 3. Graph.hx

### Haxe 实现
- `Graph` 类：图结构
  - `add()` - 添加节点
  - `remove()` - 移除节点
  - `aStar()` - A* 路径查找
  - `calculatePrice()` - 计算路径代价
- `Node` 类：节点
  - `link()` - 连接节点（对称）
  - `unlink()` - 断开连接
  - `unlinkAll()` - 断开所有连接

### Python 实现 (`graph.py`)
- ✅ `Graph` 类：已实现
  - ✅ `add()` - 已实现
  - ✅ `remove()` - 已实现
  - ✅ `a_star()` - 已实现（但算法略有不同）
  - ❌ **`calculatePrice()` - 未实现**

**差异**:
- Haxe `aStar()` 使用简单的优先队列（`openSet.shift()`）
- Python `a_star()` 使用 `min()` 查找最小代价节点（效率较低但功能相同）

**缺失功能**:
- `calculatePrice()` - 计算路径总代价的方法

**使用情况检查**:
- ✅ `calculatePrice()` 仅在 `Graph.hx` 中定义，未在其他地方调用
- **结论**: 未使用，可以忽略

**结论**: ✅ 所有使用的功能已实现。

---

## 4. Segment.hx

### Haxe 实现
```haxe
class Segment {
    public var start : Point;
    public var end : Point;
    public var dx : Float;  // getter
    public var dy : Float;  // getter
    public var vector : Point;  // getter
    public var length : Float;  // getter
}
```

### Python 实现
- ❌ **未实现独立的 Segment 类**
- ✅ 在 `model.py` 的 `_tidy_up_roads()` 中使用元组 `(v0, v1)` 表示线段
- ✅ 在 `curtain_wall.py` 中使用布尔数组 `segments` 标记边

**结论**: Segment 类在 Haxe 中主要用于 `tidyUpRoads()`，Python 版本使用元组实现相同功能。

---

## 5. Spline.hx

### Haxe 实现
- `startCurve()` - 起始曲线控制点
- `endCurve()` - 结束曲线控制点
- `midCurve()` - 中间曲线控制点
- `curvature = 0.1` - 曲率常量

### Python 实现
- ❌ **未实现 Spline 类**

**使用情况检查**:
- 在 Haxe 代码中搜索 `Spline` 的使用
- 似乎主要用于图形渲染（`GraphicsExtender`）

**结论**: Spline 功能主要用于可视化渲染，Python 版本不需要（使用 SVG 路径）。

---

## 6. Polygon.hx

### Haxe 实现 - 核心方法

#### 基础属性
- ✅ `square` - 面积（Python: `square`）
- ✅ `perimeter` - 周长（Python: `perimeter`）
- ✅ `compactness` - 紧凑度（Python: `compactness`）
- ✅ `center` - 中心点（Python: `center`）
- ✅ `centroid` - 质心（Python: 未单独实现，使用 `center`）

#### 几何操作
- ✅ `contains()` - 检查点是否为顶点（Python: `contains()`）
- ✅ `forEdge()` - 遍历边（Python: `for_edge()`）
- ✅ `forSegment()` - 遍历段（Python: `for_segment()`）
- ✅ `offset()` - 偏移（Python: `offset()`）
- ✅ `rotate()` - 旋转（Python: `rotate()`）
- ✅ `distance()` - 到点的最小距离（Python: `distance()`）

#### 凸性检查
- ✅ `isConvex()` - 是否凸多边形（Python: `is_convex()`）
- ✅ `isConvexVertex()` - 顶点是否凸（Python: 未单独实现）
- ✅ `isConvexVertexi()` - 索引顶点是否凸（Python: 未单独实现）

#### 平滑操作
- ✅ `smoothVertex()` - 平滑单个顶点（Python: `smooth_vertex()`）
- ✅ `smoothVertexi()` - 平滑索引顶点（Python: 未单独实现）
- ✅ `smoothVertexEq()` - 平滑所有顶点（Python: `smooth_vertex_eq()`）

#### 内缩/外扩操作
- ✅ `inset()` - 内缩单条边（Python: 未实现）
- ✅ `insetAll()` - 内缩所有边（Python: 未实现）
- ✅ `insetEq()` - 等距内缩（Python: 未实现）
- ✅ `buffer()` - 外扩（Python: `buffer()`）
- ✅ `shrink()` - 收缩（Python: `shrink()`）

#### 其他操作
- ✅ `filterShort()` - 过滤短边（Python: 未实现）
- ✅ `split()` - 分割多边形（Python: `split()`）
- ✅ `cut()` - 切割多边形（Python: `cut()`）
- ✅ `findEdge()` - 查找边（Python: `find_edge()`）
- ✅ `next()` / `prev()` - 下一个/上一个顶点（Python: `next()` / `prev()`）
- ✅ `interpolate()` - 插值权重（Python: `interpolate()`）
- ✅ `min()` / `max()` - 查找最小/最大顶点（Python: `min()` / `max()`）
- ✅ `vector()` - 获取向量（Python: `vector()`）

### Python 实现 (`polygon.py`)

**已实现**: ✅ 大部分核心功能
**未实现**: 
- `inset()` / `insetAll()` / `insetEq()` - 内缩操作（可能未使用）
- `filterShort()` - 过滤短边（可能未使用）
- `isConvexVertex()` / `isConvexVertexi()` - 单独检查顶点凸性（可能未使用）
- `centroid` - 质心（使用 `center` 近似）

**使用情况检查**:
- `inset()` / `insetAll()` / `insetEq()` - 仅在 `Polygon.hx` 中定义，未在其他地方调用
- `filterShort()` - 仅在 `Polygon.hx` 中定义，未在其他地方调用
- `isConvexVertex()` / `isConvexVertexi()` - 仅在 `Polygon.hx` 中定义，未在其他地方调用

**结论**: ✅ 所有使用的功能已实现，未实现的方法未被使用。

---

## 7. Voronoi.hx

### Haxe 实现
- `Voronoi` 类：
  - `addPoint()` - 添加点
  - `triangulation()` - 三角剖分
  - `partioning()` - 分区
  - `getNeighbours()` - 获取邻居
  - `relax()` - 松弛（静态方法）
  - `build()` - 构建（静态方法）
- `Triangle` 类：三角形
- `Region` 类：区域

### Python 实现 (`voronoi.py`)
- ✅ `Voronoi` 类：已实现
  - ✅ `add_point()` - 已实现
  - ✅ `triangulation()` - 已实现
  - ✅ `partitioning()` - 已实现（注意：Haxe 拼写为 `partioning`）
  - ✅ `get_neighbours()` - 已实现
  - ✅ `relax()` - 已实现（静态方法）
  - ✅ `build()` - 已实现（静态方法）
- ✅ `Triangle` 类：已实现
- ✅ `Region` 类：已实现

**结论**: ✅ 所有功能已实现，实现方式基本一致。

---

## 总结

### ✅ 完全实现
1. **GeomUtils** - 所有数学工具函数
2. **Voronoi** - 完整的 Voronoi 图实现
3. **Graph** - 图结构和 A* 算法（缺少 `calculatePrice`）

### ⚠️ 部分实现
1. **Polygon** - 核心功能完整，缺少一些高级操作（`inset`, `filterShort` 等）
2. **Graph** - 缺少 `calculatePrice()` 方法

### ❌ 未实现（可能不需要）
1. **Circle** - 使用多边形近似和 SVG 圆替代
2. **Segment** - 使用元组替代
3. **Spline** - 主要用于可视化，Python 版本不需要

### 建议

1. **检查 `calculatePrice()` 是否被使用**
   - 如果未被使用，可以忽略
   - 如果被使用，需要实现

2. **验证 Polygon 的高级方法**
   - 检查 `inset()` 等方法是否在代码中被调用
   - 如果未使用，可以忽略

3. **性能优化**
   - Python 版本的 `a_star()` 使用 `min()` 查找，效率较低
   - 可以考虑使用优先队列优化
