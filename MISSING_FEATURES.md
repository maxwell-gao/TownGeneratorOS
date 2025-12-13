# 缺失功能对比清单

本文档对比了 Haxe 原始实现和 Python 重构版本，列出可能缺失或实现不一致的功能。

## 核心功能对比

### ✅ 已实现的功能

1. **Model 类核心方法**
   - ✅ `buildPatches()` → `_build_patches()`
   - ✅ `optimizeJunctions()` → `_optimize_junctions()`
   - ✅ `buildWalls()` → `_build_walls()`
   - ✅ `buildStreets()` → `_build_streets()`
   - ✅ `createWards()` → `_create_wards()`
   - ✅ `buildGeometry()` → `_build_geometry()`
   - ✅ `findCircumference()` → `find_circumference()` (已优化)
   - ✅ `tidyUpRoads()` → `_tidy_up_roads()`
   - ✅ `smoothStreet()` → `smooth_street()` (内联函数)
   - ✅ `patchByVertex()` → `patch_by_vertex()`
   - ✅ `getNeighbour()` → `get_neighbour()`
   - ✅ `getNeighbours()` → `get_neighbours()`
   - ✅ `isEnclosed()` → `is_enclosed()`

2. **Ward 类方法**
   - ✅ `createGeometry()` → `create_geometry()`
   - ✅ `getCityBlock()` → `get_city_block()`
   - ✅ `filterOutskirts()` → `filter_outskirts()`
   - ✅ `createAlleys()` → `create_alleys()`
   - ✅ `createOrthoBuilding()` → `create_ortho_building()`
   - ✅ `getLabel()` → `get_label()`
   - ✅ `rateLocation()` → `rate_location()`

3. **Ward 子类**
   - ✅ `CraftsmenWard`
   - ✅ `MerchantWard`
   - ✅ `Slum`
   - ✅ `Market`
   - ✅ `Castle`
   - ✅ `GateWard`
   - ✅ `AdministrationWard`
   - ✅ `MilitaryWard`
   - ✅ `PatriciateWard`
   - ✅ `Park`
   - ✅ `Cathedral`
   - ✅ `Farm`
   - ✅ `CommonWard` (基类)

4. **工具类**
   - ✅ `Random` (包括 `fuzzy()`)
   - ✅ `Polygon` (包括 `smoothVertexEq()`)
   - ✅ `Point`
   - ✅ `Voronoi`
   - ✅ `Topology`
   - ✅ `CurtainWall`
   - ✅ `Cutter`

## ⚠️ 需要进一步验证的功能

### 1. `tidyUpRoads()` 实现细节
**Haxe 实现** (`Model.hx:257-306`):
- 使用 `Segment` 类来表示线段
- 通过 `seg.start` 和 `seg.end` 访问端点
- 使用 `a.unshift()` 和 `a.last()` 操作

**Python 实现** (`model.py:284-335`):
- 使用元组 `(v0, v1)` 表示线段
- 使用 `a[0]` 和列表操作
- **需要验证**: 逻辑是否完全一致

### 2. `filterOutskirts()` 中的 `interpolate()` 方法
**Haxe** (`Ward.hx:111`):
```haxe
var i = patch.shape.interpolate( c );
```

**Python** (`ward.py:125-159`):
- 需要检查 `polygon.interpolate()` 的实现是否匹配

### 3. `smoothStreet()` 中的 `smoothVertexEq()`
**Haxe** (`Model.hx:214`):
```haxe
var smoothed = street.smoothVertexEq( 3 );
```

**Python** (`model.py:245`):
```python
smoothed = street.smooth_vertex_eq(3)
```
- ✅ 已实现，但需要验证参数和算法是否一致

## 🔍 可能缺失的功能（需要进一步检查）

### 1. UI 和可视化相关（预期缺失）
以下功能在 Haxe 中用于 UI 显示，Python 版本可能不需要：
- `mapping/` 目录下的所有类 (`CityMap`, `Palette`, `PatchView`, `Brush`)
- `ui/` 目录下的所有类 (`Button`, `CitySizeButton`, `Tooltip`)
- `TownScene.hx` - 场景管理
- `StateManager.hx` - 状态管理
- `coogee/` 目录 - 游戏引擎相关

### 2. 工具类扩展方法
Haxe 使用了扩展方法（using）：
- `PointExtender` - Point 的扩展方法
- `ArrayExtender` - Array 的扩展方法
- `FloatExtender` - Float 的扩展方法

**需要检查**: Python 版本是否实现了所有必要的扩展方法功能。

### 3. 其他工具类
- `PerlinNoise` - 噪声生成（如果未使用，可能不需要）
- `MarkovChain` - 马尔可夫链（如果未使用，可能不需要）
- `MathUtils` - 数学工具（部分功能可能在 `math_utils.py` 中）

## 📝 建议检查项

1. **验证 `_tidy_up_roads()` 的逻辑**
   - 检查线段连接逻辑是否与 Haxe 版本一致
   - 验证 `arteries` 的构建方式

2. **验证 `filter_outskirts()` 的完整实现**
   - 检查 `interpolate()` 方法的实现
   - 验证密度计算和建筑过滤逻辑

3. **检查所有 Ward 子类的 `rateLocation()` 方法**
   - 确保所有子类都正确实现了位置评分

4. **验证 `smooth_vertex_eq()` 算法**
   - 确保平滑算法与 Haxe 版本一致

5. **检查边界情况处理**
   - 空列表、单点、异常输入等情况的处理

## 📋 Main.hx 和入口点对比

### Haxe Main.hx (`Source/com/watabou/towngenerator/Main.hx`)

**功能**:
- 继承自 `Game` 类（游戏引擎）
- 初始化 UI 字体和场景
- 使用 `StateManager` 管理参数（size, seed）
- 创建 `Model` 实例
- 显示 `TownScene`（可视化场景）

**关键代码**:
```haxe
new Model( StateManager.size, StateManager.seed );
super( TownScene );
```

**StateManager 功能**:
- `pullParams()`: 从 URL 参数读取 size 和 seed（HTML5 版本）
- `pushParams()`: 更新 URL 参数，保存状态
- `getStateName()`: 根据 size 返回城市类型名称（"Small Town", "Large Town" 等）

### Python main.py

**功能**:
- 命令行参数解析（argparse）
- 创建 `Model` 实例
- 导出 JSON（`export_to_json`）
- 打印统计信息

**关键差异**:
- ✅ **JSON 导出**: Python 版本有完整的 JSON 导出功能（Haxe 版本没有）
- ❌ **StateManager**: Python 版本不需要（命令行参数替代）
- ❌ **UI/可视化**: Python 版本使用独立的 `visualize.py` 脚本
- ✅ **参数验证**: Python 版本有 size 范围验证（6-40）

### 发现

1. **Haxe 版本没有 JSON 导出功能**
   - Haxe 版本主要用于实时可视化显示
   - 所有数据都在内存中，通过 `CityMap` 渲染
   - Python 版本的 JSON 导出是新增功能

2. **StateManager 的功能**
   - Haxe: 用于 Web 版本的 URL 参数管理
   - Python: 不需要，使用命令行参数即可

3. **城市类型名称映射**
   - Haxe `getStateName()`:
     - 6-9: "Small Town"
     - 10-14: "Large Town"
     - 15-23: "Small City"
     - 24-39: "Large City"
     - 40+: "Metropilis" (注意拼写)
   - Python: 没有实现此功能（可能不需要）

## 🎯 总结

从代码结构来看，Python 版本已经实现了 Haxe 版本的核心功能。主要差异在于：

1. **UI/可视化相关功能** - 这些在 Python 版本中不需要（有独立的 `visualize.py`）
2. **实现细节** - 需要仔细验证一些算法的实现是否完全一致
3. **扩展方法** - Haxe 的扩展方法在 Python 中通过直接方法实现
4. **JSON 导出** - Python 版本新增的功能（Haxe 版本没有）
5. **入口点** - Haxe 版本是游戏应用，Python 版本是命令行工具

建议重点检查 `tidyUpRoads` 和 `filterOutskirts` 的实现细节，确保逻辑完全一致。
