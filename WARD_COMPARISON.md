# Ward 类功能对比分析

本文档详细对比了 Haxe Ward 类实现和 Python 版本的对应实现。

## 1. Ward.hx (基类)

### Haxe 实现
- `createGeometry()` - 创建几何（空实现）
- `getCityBlock()` - 获取城市街区多边形
- `filterOutskirts()` - 过滤郊区建筑
- `createAlleys()` - 创建小巷
- `createOrthoBuilding()` - 创建正交建筑
- `getLabel()` - 获取标签（返回 null）
- `rateLocation()` - 位置评分（返回 0）

### Python 实现 (`ward.py`)
- ✅ `create_geometry()` - 已实现
- ✅ `get_city_block()` - 已实现
- ✅ `filter_outskirts()` - 已实现
- ✅ `create_alleys()` - 已实现
- ✅ `create_ortho_building()` - 已实现
- ✅ `get_label()` - 已实现
- ✅ `rate_location()` - 已实现

**结论**: ✅ 所有基类功能已实现

---

## 2. CommonWard.hx

### Haxe 实现
```haxe
class CommonWard extends Ward {
    private var minSq : Float;
    private var gridChaos : Float;
    private var sizeChaos : Float;
    private var emptyProb : Float;
    
    override public function createGeometry() {
        var block = getCityBlock();
        geometry = Ward.createAlleys( block, minSq, gridChaos, sizeChaos, emptyProb );
        if (!model.isEnclosed( patch ))
            filterOutskirts();
    }
}
```

### Python 实现
- ✅ 完全匹配 Haxe 实现

**结论**: ✅ 实现一致

---

## 3. CraftsmenWard.hx

### Haxe 实现
```haxe
super( model, patch,
    10 + 80 * Random.float() * Random.float(),  // minSq
    0.5 + Random.float() * 0.2,                 // gridChaos
    0.6 );                                       // sizeChaos
```

### Python 实现
```python
min_sq = 10 + 80 * Random.float() * Random.float()
grid_chaos = 0.5 + Random.float() * 0.2
size_chaos = 0.6
```

**结论**: ✅ 参数完全一致

---

## 4. Slum.hx

### Haxe 实现
```haxe
super( model, patch,
    10 + 30 * Random.float() * Random.float(),  // minSq
    0.6 + Random.float() * 0.4,                 // gridChaos
    0.8,                                         // sizeChaos
    0.03 );                                      // emptyProb

public static function rateLocation( model:Model, patch:Patch ):Float
    return -patch.shape.distance( model.plaza != null ? model.plaza.shape.center : model.center );
```

### Python 实现
- ✅ 参数一致
- ✅ `rate_location()` 已实现

**结论**: ✅ 实现一致

---

## 5. Market.hx

### Haxe 实现
```haxe
override public function createGeometry() {
    var statue = Random.bool( 0.6 );
    var offset = statue || Random.bool( 0.3 );
    
    // Find longest edge
    var v0:Point = null;
    var v1:Point = null;
    if (statue || offset) {
        var length = -1.0;
        patch.shape.forEdge( function( p0, p1 ) {
            var len = Point.distance( p0, p1 );
            if (len > length) {
                length = len;
                v0 = p0;
                v1 = p1;
            }
        } );
    }
    
    var object:Polygon;
    if (statue) {
        object = Polygon.rect( 1 + Random.float(), 1 + Random.float() );
        object.rotate( Math.atan2( v1.y - v0.y, v1.x - v0.x ) );
    } else {
        object = Polygon.circle( 1 + Random.float() );
    }
    
    if (offset) {
        var gravity = GeomUtils.interpolate( v0, v1 );
        object.offset( GeomUtils.interpolate( patch.shape.centroid, gravity, 0.2 + Random.float() * 0.4 ) );
    } else {
        object.offset( patch.shape.centroid );
    }
    
    geometry = [object];
}

public static function rateLocation( model:Model, patch:Patch ):Float {
    // One market should not touch another
    for (p in model.inner)
        if (Std.is( p.ward, Market ) && p.shape.borders( patch.shape ))
            return Math.POSITIVE_INFINITY;
    
    // Market shouldn't be much larger than the plaza
    return model.plaza != null ? patch.shape.square / model.plaza.shape.square : patch.shape.distance( model.center );
}
```

### Python 实现
- ✅ `create_geometry()` - 已实现，逻辑一致
- ✅ `rate_location()` - 已实现，逻辑一致

**差异**:
- Haxe 使用 `GeomUtils.interpolate( v0, v1 )` (默认 ratio=0.5)
- Python 使用 `geom_interpolate(v0, v1, 0.5)` (显式指定)

**结论**: ✅ 实现一致

---

## 6. Castle.hx

### Haxe 实现
```haxe
public var wall : CurtainWall;

public function new( model:Model, patch:Patch ) {
    super( model, patch );
    
    wall = new CurtainWall( true, model, [patch], patch.shape.filter(
        function( v:Point ) return model.patchByVertex( v ).some(
            function( p:Patch ) return !p.withinCity
        )
    ) );
}

override public function createGeometry() {
    var block = patch.shape.shrinkEq( Ward.MAIN_STREET * 2 );
    geometry = Ward.createOrthoBuilding( block, Math.sqrt( block.square ) * 4, 0.6 );
}
```

### Python 实现
- ✅ `wall` 属性已实现
- ✅ `create_geometry()` 已实现
- ✅ 使用 `shrink_eq()` 方法

**结论**: ✅ 实现一致

---

## 7. Cathedral.hx

### Haxe 实现
```haxe
override public function createGeometry()
    geometry = Random.bool( 0.4 ) ?
        Cutter.ring( getCityBlock(), 2 + Random.float() * 4 ) :
        Ward.createOrthoBuilding( getCityBlock(), 50, 0.8 );

public static function rateLocation( model:Model, patch:Patch ):Float
    return if (model.plaza != null && patch.shape.borders( model.plaza.shape ))
        -1/patch.shape.square
    else
        patch.shape.distance( model.plaza != null ? model.plaza.shape.center : model.center ) * patch.shape.square;
```

### Python 实现
```python
def create_geometry(self):
    block = self.patch.shape.shrink_eq(self.MAIN_STREET)
    self.geometry = [block]  # Simplified
```

**问题**:
- ❌ **未实现 `Cutter.ring()` 方法**
- ❌ **未实现 `rateLocation()` 方法**
- ❌ **创建逻辑简化，未使用 `Cutter.ring()` 或 `createOrthoBuilding()`**

**结论**: ⚠️ **实现不完整**

---

## 8. Farm.hx

### Haxe 实现
```haxe
override public function createGeometry() {
    var housing = Polygon.rect( 4, 4 );
    var pos = GeomUtils.interpolate( patch.shape.random(), patch.shape.centroid, 0.3 + Random.float() * 0.4 );
    housing.rotate( Random.float() * Math.PI );
    housing.offset( pos );
    
    geometry = Ward.createOrthoBuilding( housing, 8, 0.5 );
}
```

### Python 实现
```python
def create_geometry(self):
    self.geometry = []
```

**问题**:
- ❌ **未实现 Farm 的几何创建逻辑**
- ❌ **缺少 `patch.shape.random()` 方法**
- ❌ **缺少 `patch.shape.centroid` 属性**

**结论**: ⚠️ **实现不完整**

---

## 9. GateWard.hx

### Haxe 实现
```haxe
super( model, patch,
    10 + 50 * Random.float() * Random.float(),  // minSq
    0.5 + Random.float() * 0.3,                // gridChaos
    0.7 );                                      // sizeChaos
```

### Python 实现
```python
min_sq = 15 + 60 * Random.float() * Random.float()
grid_chaos = 0.4 + Random.float() * 0.3
size_chaos = 0.7
```

**差异**:
- Haxe: `minSq = 10 + 50 * ...`
- Python: `min_sq = 15 + 60 * ...`

**结论**: ⚠️ **参数不一致**

---

## 10. MerchantWard.hx

### Haxe 实现
```haxe
super( model, patch,
    50 + 60 * Random.float() * Random.float(),  // minSq
    0.5 + Random.float() * 0.3,                 // gridChaos
    0.7,                                         // sizeChaos
    0.15 );                                      // emptyProb

public static function rateLocation( model:Model, patch:Patch )
    return patch.shape.distance( model.plaza != null ? model.plaza.shape.center : model.center );
```

### Python 实现
```python
min_sq = 20 + 100 * Random.float() * Random.float()
grid_chaos = 0.3 + Random.float() * 0.2
size_chaos = 0.5
# 缺少 emptyProb = 0.15
# 缺少 rate_location()
```

**问题**:
- ❌ **参数不一致** (minSq, gridChaos, sizeChaos 都不同)
- ❌ **缺少 `emptyProb = 0.15`**
- ❌ **缺少 `rateLocation()` 方法**

**结论**: ⚠️ **实现不完整且参数不一致**

---

## 11. AdministrationWard.hx

### Haxe 实现
```haxe
super( model, patch,
    80 + 30 * Random.float() * Random.float(),  // minSq
    0.1 + Random.float() * 0.3,                 // gridChaos
    0.3 );                                       // sizeChaos

public static function rateLocation( model:Model, patch:Patch ):Float
    return model.plaza != null ?
        (patch.shape.borders( model.plaza.shape ) ? 0 : patch.shape.distance( model.plaza.shape.center )) :
        patch.shape.distance( model.center );
```

### Python 实现
```python
min_sq = 30 + 120 * Random.float() * Random.float()
grid_chaos = 0.2 + Random.float() * 0.2
size_chaos = 0.4
# 缺少 rate_location()
```

**问题**:
- ❌ **参数不一致** (所有参数都不同)
- ❌ **缺少 `rateLocation()` 方法**

**结论**: ⚠️ **实现不完整且参数不一致**

---

## 12. MilitaryWard.hx

### Haxe 实现
```haxe
override public function createGeometry() {
    var block = getCityBlock();
    geometry = Ward.createAlleys( block,
        Math.sqrt( block.square ) * (1 + Random.float()),
        0.1 + Random.float() * 0.3,  // gridChaos
        0.3,                           // sizeChaos
        0.25 );                        // emptyProb (squares)
}

public static function rateLocation( model:Model, patch:Patch ):Float
    return
        if (model.citadel != null && model.citadel.shape.borders( patch.shape ))
            0
        else if (model.wall != null && model.wall.borders( patch ))
            1
        else
            (model.citadel == null && model.wall == null ? 0 : Math.POSITIVE_INFINITY);
```

### Python 实现
```python
class MilitaryWard(CommonWard):  # 继承自 CommonWard
    def __init__(self, model, patch):
        min_sq = 25 + 100 * Random.float() * Random.float()
        grid_chaos = 0.3 + Random.float() * 0.2
        size_chaos = 0.5
        super().__init__(model, patch, min_sq, grid_chaos, size_chaos)
```

**问题**:
- ❌ **继承关系错误**: Haxe 版本继承自 `Ward`，Python 版本继承自 `CommonWard`
- ❌ **`createGeometry()` 逻辑完全不同**: Haxe 使用特殊的 `createAlleys()` 调用，Python 使用 CommonWard 的默认实现
- ❌ **缺少 `rateLocation()` 方法**

**结论**: ⚠️ **实现严重不一致**

---

## 13. Park.hx

### Haxe 实现
```haxe
override public function createGeometry() {
    var block = getCityBlock();
    geometry = block.compactness >= 0.7 ?
        Cutter.radial( block, null, Ward.ALLEY ) :
        Cutter.semiRadial( block, null, Ward.ALLEY );
}
```

### Python 实现
```python
def create_geometry(self):
    block = self.get_city_block()
    self.geometry = [block]  # Simplified
```

**问题**:
- ❌ **未实现 `Cutter.radial()` 方法**
- ❌ **未实现 `Cutter.semiRadial()` 方法**
- ❌ **创建逻辑简化**

**结论**: ⚠️ **实现不完整**

---

## 14. PatriciateWard.hx

### Haxe 实现
```haxe
super( model, patch,
    80 + 30 * Random.float() * Random.float(),  // minSq
    0.5 + Random.float() * 0.3,                 // gridChaos
    0.8,                                         // sizeChaos
    0.2 );                                       // emptyProb

public static function rateLocation( model:Model, patch:Patch ):Float {
    var rate = 0;
    for (p in model.patches) if (p.ward != null && p.shape.borders( patch.shape )) {
        if (Std.is( p.ward, Park ))
            rate--
        else if (Std.is( p.ward, Slum ))
            rate++;
    }
    return rate;
}
```

### Python 实现
```python
min_sq = 40 + 150 * Random.float() * Random.float()
grid_chaos = 0.2 + Random.float() * 0.2
size_chaos = 0.3
# 缺少 emptyProb = 0.2
# 缺少 rate_location()
```

**问题**:
- ❌ **参数不一致** (所有参数都不同)
- ❌ **缺少 `emptyProb = 0.2`**
- ❌ **缺少 `rateLocation()` 方法** (复杂的邻居评分逻辑)

**结论**: ⚠️ **实现不完整且参数不一致**

---

## 总结

### ✅ 完全实现的 Ward 类
1. **Ward** (基类)
2. **CommonWard**
3. **CraftsmenWard**
4. **Slum**
5. **Market**
6. **Castle**

### ⚠️ 部分实现的 Ward 类
1. **Cathedral** - 缺少 `Cutter.ring()` 和 `rateLocation()`
2. **Farm** - 缺少完整的几何创建逻辑
3. **Park** - 缺少 `Cutter.radial()` 和 `Cutter.semiRadial()`

### ⚠️ 参数不一致的 Ward 类
1. **GateWard** - minSq 参数不同
2. **MerchantWard** - 所有参数都不同，缺少 `emptyProb` 和 `rateLocation()`
3. **AdministrationWard** - 所有参数都不同，缺少 `rateLocation()`
4. **PatriciateWard** - 所有参数都不同，缺少 `emptyProb` 和 `rateLocation()`

### ❌ 实现严重不一致的 Ward 类
1. **MilitaryWard** - 继承关系错误，`createGeometry()` 逻辑完全不同

### 缺失的功能
1. **Cutter.ring()** - 环形切割（用于 Cathedral）
2. **Cutter.radial()** - 径向切割（用于 Park）
3. **Cutter.semiRadial()** - 半径向切割（用于 Park）
4. **Polygon.random()** - 随机顶点选择（用于 Farm）- Haxe 中通过 `ArrayExtender.random()` 实现，Python 可用 `random.choice(polygon.vertices)`
5. **Polygon.centroid** - ✅ 已实现（用于 Farm, Market）
6. **多个 `rateLocation()` 方法** - 位置评分逻辑

### 建议修复优先级

**高优先级**:
1. 修复 `MilitaryWard` 的继承关系和 `createGeometry()` 逻辑
2. 实现 `Cathedral.rateLocation()`
3. 实现 `MerchantWard.rateLocation()`
4. 实现 `AdministrationWard.rateLocation()`
5. 实现 `PatriciateWard.rateLocation()`

**中优先级**:
6. 实现 `Cutter.ring()`, `Cutter.radial()`, `Cutter.semiRadial()`
7. 修复 `Cathedral.createGeometry()` 使用 `Cutter.ring()`
8. 修复 `Park.createGeometry()` 使用径向切割
9. 修复 `Farm.createGeometry()` 完整逻辑

**低优先级**:
10. 统一所有 Ward 类的参数值
11. 添加 `Polygon.random()` 和 `Polygon.centroid` 属性
