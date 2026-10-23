# 隔离运行与全规格扩展

本文件对应 `scripts/stata_runner.py`、`assets/oc_collect.ado`。它们是本技能新增工具，不属于作者 OneClick。需要真实的 Python 3.9+、可调用的 Stata 及相应估计器；不使用 Python 模拟回归结果。Windows Stata 18 已实际测试，其他系统的批处理分支尚未实测。

## 选择入口

| engine | 工作方式 | 输出含义 |
| --- | --- | --- |
| `oneclick` | 在独立 Stata 会话中加载已核验的原版 6.0，再调用原命令 | 仍然只有原算法筛出的显著非空组合；p仍是星号，不补造精确p、失败数或N |
| `fullspec` | 直接按组合大小枚举并逐条估计，不调用oneclick | 每个计划规格一行，含空组合（默认）、不显著、估计失败及推断无效的规格 |

根据任务选择入口。用户要全部规格时选 `fullspec`，不要把原版 `full` 选项当作这一功能。

## 教学数据的实际调用

先找到可用解释器；Windows裸 `python` 可能是商店占位符。以下 `$pythonExe` 应指向已经确认可用的Python，`$skillDir` 指向安装目录：

```powershell
$skillDir = Join-Path $env:USERPROFILE '.codex\skills\gehua-chen'
& $pythonExe "$skillDir\scripts\stata_runner.py" plan "$skillDir\assets\fullspec_auto.json" --output-root '.\oneclick-runs'
& $pythonExe "$skillDir\scripts\stata_runner.py" run "$skillDir\assets\fullspec_auto.json" --output-root '.\oneclick-runs'
```

可用 `--stata` 指定实际可执行文件路径；未指定时，执行器查 `STATA_EXE`、PATH及Windows卸载注册表。程序名含MP不证明实际许可类型，以输出 `c(flavor)` 为准。`plan`只生成配置、命令计划和do文件，不启动Stata；`run`生成一个新的运行目录后执行。可先查看计划，再对同一配置运行；两次会产生不同目录。

`fullspec_auto.json`：price为y，weight为目标x，mpg/rep78为候选，稳健标准误、共同完整案例样本。计划4条：无候选、仅mpg、仅rep78、两者都有。“无候选”仍包含目标x、固定控制项和默认截距。

原版入口需在配置中设置 `engine: "oneclick"`、`min_controls: 1`，删除 `max_controls` 等扩展专用参数。执行时额外传：

```powershell
--ado-dir '保存官方oneclick.ado的目录'
```

只接受 [来源清单](source-manifest.json) 已核验字节的OneClick 6.0；哈希不同先复核版本。本工具不下载或安装命令、不修改个人ado目录。原版 `threshold` 至少1，故本入口不会调用原版的空组合估计。原版还会分配全部 `2^k` 组合位置，单独受 `max_original_slots` 限制。

## JSON配置

使用用户授权的数据文件、变量角色与基准模型，不从磁盘随意挑数据运行。相对 `data_path` 以JSON文件所在目录解析。文件必须是本地 `.dta`；与 `data_source: "auto"` 二选一。未开放任意Stata代码、自由文本options、if/in、权重或数据清洗命令，需要这些时在独立do中明确实现和验证。

| 字段 | 取值与含义 |
| --- | --- |
| `engine` | `fullspec`（默认）或`oneclick` |
| `data_source` / `data_path` | 自带`auto`或明确的`.dta`路径 |
| `outcome`, `target` | 单个简单变量名；目标必须是可单独检验的数值系数 |
| `candidates` | 简单数值变量名列表，顺序固定；原版至少2个，扩展可为0个 |
| `fixed_controls` | 始终保留，支持简单数值变量、`i.name`、`c.name`；暂不支持交互/时序表达式 |
| `method` | `regress`（默认）、`xtreg`、`reghdfe`、`logit`、`probit` |
| `fixed_effects` | 仅供`reghdfe`的`absorb()`变量列表；其他模型用固定控制中的`i.year`等 |
| `panel_id`, `time_var`, `panel_model` | 仅供`xtreg`；id及`fe`/`re`必填，时间变量可选 |
| `vce` | `{"type":"conventional"}`、`{"type":"robust"}`或`{"type":"cluster","cluster_var":"id"}` |
| `sample_policy` | `common`（默认）：按全部配置变量完整案例建立输入池；`per_spec`：由各估计器使用自己的可用样本 |
| `min_controls` | 扩展默认0；原版默认1，对应`threshold()` |
| `max_controls` | 仅扩展，默认候选数；限制枚举的最大组合大小 |
| `alpha` | 默认.05，严格`p<alpha`；扩展只记录标记，不据此删行 |
| `max_models` | 默认256，超过预算在启动Stata前拒绝；可根据任务明确调高，上限100000 |
| `max_original_slots` | 仅原版，默认65536，最大1048576；不被threshold绕过 |
| `zvalue`, `full`, `best` | 仅原版，默认false/true/false；Logit/Probit原版须显式`zvalue:true`；扩展用原生`lincom`，不接受这些开关 |

配置未知键、重叠变量角色、重复候选、无效路径/宏字符、超长命令等会被拒绝。数值变量检查、面板唯一性、估计器依赖及其他数据条件在Stata中核验；不自动改模型使之通过。`xtreg,re`接口可生成，但本轮运行验收覆盖的是`fe`。

面板聚类示例（实际数据路径和变量名由任务提供）：

```json
{
  "engine": "fullspec",
  "data_path": "panel.dta",
  "outcome": "y",
  "target": "x",
  "candidates": ["c1", "c2"],
  "fixed_controls": ["i.year"],
  "method": "xtreg",
  "panel_id": "id",
  "time_var": "year",
  "panel_model": "fe",
  "vce": {"type": "cluster", "cluster_var": "id"},
  "sample_policy": "common",
  "min_controls": 0,
  "max_models": 16
}
```

## 输出与完成判定

每次在指定输出根目录下新建 `run-UTC时间-随机标识`，不覆盖已有运行。保留 `config.json`、`plan.json`、`job.do`、Stata的`job.log`、`input_status.txt`、`run_status.txt`和`manifest.json`。manifest记录实际软件版本/类型、源文件与输入数据哈希、运行时间、状态与结果数量。输出可能含本机路径和研究信息，分享时按实际需要处理。

扩展输出 `all_specs.dta` 和 `all_specs.csv`；原版输出 `oneclick_selected.dta/csv`。不写回输入文件；运行结束核对本地输入DTA的SHA-256。每个子会话有自己的内存与工作目录，不在用户已打开的Stata会话中 `clear`。Windows子进程隐藏启动，无全局包安装。

进程退出码0不是成功的充分条件。工具必须同时读到本次完成标记、`job_rc=0`、预期CSV及与计划完全一致的扩展规格顺序/命令。运行级错误写为`failed`；默认300秒超时，可用 `--timeout 秒数` 修改，只终止本工具启动的子进程并标`timed_out`。这两种情况不能当完整结果。不会为获得显著结果自动重试或改阈值。

扩展“运行完成”可以包含模型失败：每行状态被保留。应先看manifest状态计数和每行status，再解释统计量。原版完成只代表其算法成功产生选中输出，不证明没有失败规格，也未自动为每个选中规格补做独立回验。

## 扩展结果字段

| 字段 | 含义 |
| --- | --- |
| `spec_id`, `control_count`, `subset`, `command` | 按组合大小、候选顺序生成的确定性计划；与原版二进制次序不同 |
| `estimation_rc`, `inference_rc`, `status` | 估计命令实际返回码、尝试`lincom`时的实际返回码、细化状态；未尝试时返回码缺失 |
| `N`, `sample_used_N` | 估计器e(N)、按e(sample)计数；失败时缺失 |
| `b`, `se`, `statistic` | 目标系数、标准误、b/SE，使用double，不从显示文本或星号反推 |
| `df_r`, `df_test`, `p_value` | 估计残差自由度、原生`lincom`的检验自由度、原生双侧p；z检验的df可缺失 |
| `ci_low`, `ci_high` | 原生`lincom`的95%区间，固定95%，不随筛选alpha改变 |
| `r2`, `r2_a`, `r2_p`, `ll` | 普通R²、调整R²、伪R²、对数似然，分别保留；缺什么就缺什么，不互相替代 |
| `converged` | e(converged)，估计器不提供时缺失 |
| `common_pool_complete` | common策略中，实际e(sample)是否用尽输入池；per_spec时缺失 |
| `passes_alpha` | 仅对有效推断记录p是否严格小于alpha；不影响行保留 |

状态可能为`ok`、`estimation_failed`、`target_absent`、`target_omitted`、`omission_check_failed`、`invalid_standard_error`、`not_converged`、`inference_failed`、`invalid_inference`。估计失败的统计量全部缺失；推断无效时p/区间/阈值标记缺失，已有的估计量或诊断可以保留。具体错误文本在对应SPEC编号的日志位置，返回码并不是唯一病因。

每个规格先清空e()并重置所有结果，避免失败时沿用前一次结果。共线省略检查使用`_ms_omit_info`，不把0/0视为有效检验。扩展仅支持上表估计器；不泛化到多方程或指数化系数显示命令如`logistic`。

共同输入池不一定意味着实际样本完全相同：单例删除、完全预测等仍可能让估计器删观测。检查`common_pool_complete`；如为0，不能将其称为严格同样本比较。`per_spec`中相同N也不证明是相同观测，必要时另存样本成员，当前CSV未保存逐观察样本掩码。

## 检验与依据

测试脚本见 [测试记录](tests/report.md)。预算和输入验证测试不需要Stata；集成测试只使用auto与固定种子的合成数据，需显式设置`STATA_EXE`，原版测试还需`ONECLICK_ADO_DIR`。结果目录可通过`STATA_TEST_ROOT`指定。

原生批处理语法参考 [Stata Windows batch mode](https://www.stata.com/support/faqs/windows/batch-mode/)。推断与省略项依据本机官方`lincom.sthlp`、`lincom.ado`和`_ms_omit_info.sthlp`，另见 [Stata因子变量编程说明](https://www.stata.com/support/faqs/programming/factor-variable-support/)。自动执行接口和字段是本技能设计，不能归为视频作者的承诺。
