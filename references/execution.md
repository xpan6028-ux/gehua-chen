# 隔离运行与全规格扩展

本文件对应技能根目录中的`scripts/stata_runner.py`与`assets/oc_collect.ado`，均为本技能扩展，不属于作者OneClick。只讲解或写代码不需要这些运行依赖；调用`plan`仅需Python3.9+；调用`run`才需要当前宿主有文件/进程能力、实际数据、可用Stata与相应估计器。Windows Stata18已实测，其他系统分支尚未实测。

## 选择入口

| engine | 工作方式 | 输出含义 |
| --- | --- | --- |
| `oneclick` | 在独立 Stata 会话中加载已核验的原版 6.0，再调用原命令 | 仍然只有原算法筛出的显著非空组合；p仍是星号，不补造精确p、失败数或N |
| `fullspec` | 直接按组合大小枚举并逐条估计，不调用oneclick | 每个计划规格一行，含空组合（默认）、不显著、估计失败及推断无效的规格 |

根据任务选择入口。用户要全部规格时选 `fullspec`，不要把原版 `full` 选项当作这一功能。

## 路径解析：适用于不同AI宿主

1. 从当前宿主读取`SKILL.md`返回的实际绝对路径取其父目录，作为技能根目录。若宿主给了注册目录则直接核对其中的`SKILL.md`。不要用当前工作目录、`~/.codex`或某个豆包目录代替这个实际位置。只有文档文字、没有磁盘位置时，先明确缺少的路径；不要假装已安装。
2. 从当前工具提供的运行时或PATH确认真实Python3.9+，记录其`sys.executable`绝对路径。Windows商店占位符不算可用解释器。检查失败时可检查一个明确的替代运行时，仍不可用就交付文字计划或do；不全盘搜索/循环重装环境。
3. 拼出根目录下`scripts/stata_runner.py`及配置文件的绝对路径。输出根目录取用户指定位置，或在已授权的项目目录中新建明确的结果目录，然后也转绝对路径。外部数据尽量在JSON中填绝对`data_path`。
4. 调用形式是“Python绝对路径、入口脚本绝对路径、动作plan/run、配置绝对路径、--output-root、输出绝对路径”。使用工具支持的参数数组；必须经shell时正确引用带空格/中文的路径。AI呈现给用户的最终命令应是本机已解析值，不能原样复制占位符或未定义变量。

脚本用自身`__file__`定位内部资源；生成的`job.do`包含运行目录的绝对`cd`，启动Stata也使用该do的绝对路径。目录结构中的相对名称用于说明文件位置，不代表要求调用方先切换工作目录。

Windows还提供[run_demo.ps1](../scripts/run_demo.ps1)，入口自身通过`$PSScriptRoot`定位技能，参数为`-Action plan/run`、必填的绝对`-OutputRoot`、可选绝对`-PythonExe`、可选`-Stata`和超时。没有显式Python时仅检查PATH上的python/python3/py，不假定某家AI的私有安装目录；检查失败就明确退出。AI应使用该ps1的实际绝对路径调用。若宿主不允许运行ps1，直接用上面的Python入口，不改变系统执行策略。人类用户安装后可复制运行的完整示例见[README](../README.md)。

`--stata`可给实际可执行文件路径或PATH上的命令名；未指定时查`STATA_EXE`、PATH及Windows卸载注册表。程序名含MP不证明实际许可类型，以`c(flavor)`为准。Python与Stata可以在不同目录。能导入技能、能在云沙箱运行Python，都不证明能访问用户电脑的Stata。

`plan`只生成配置、计划与do，不启动Stata，不检查许可/估计器，不读取DTA内容或强制要求DTA已存在。用户只要变量组合时，不因未提供数据而卡住。`run`重新检查数据和环境；计划成功不是执行前置条件已通过的证明。用户已要求运行时，可以直接调用run，不必先另起一次plan或请求重复确认。

`fullspec_auto.json`：price为y，weight为目标x，mpg/rep78为候选，稳健标准误、共同完整案例样本。计划4条：无候选、仅mpg、仅rep78、两者都有。“无候选”仍包含目标x、固定控制项和默认截距。

原版入口在配置中设置`engine: "oneclick"`、`min_controls: 1`，不传`max_controls`等扩展专用字段。原版**run**额外需要`--ado-dir`指向已核验源码目录的绝对路径；原版**plan**不需要这个目录，也不要求安装OneClick。fullspec的plan/run均不需要OneClick。

此包装器的原版run只接受[来源清单](source-manifest.json)已核验字节的6.0。`ssc install`可供用户直接在Stata使用，但“全局已安装”不能自动满足包装器的固定哈希ado目录条件；不要在两种安装方式之间无限重试。版本不符时说明差异并停止该入口，或按用户实际版本交付独立命令。源码目录必须能从当前Stata进程访问；不自动下载安装。原版至少两个候选且`min_controls>=1`，仍分配全部`2^k`组合位置，由`max_original_slots`另行限制。

## JSON配置

使用用户授权的文件、变量角色与基准模型。run要求`data_path`与`data_source: "auto"`二选一；前者须以`.dta`结尾并且存在可读。plan允许路径指向尚未提供的DTA，也允许两个数据字段均不填：只生成组合计划，并在do中明确缺少数据，不能偷偷改用auto示例代替用户研究。输入为Excel/CSV时不把它改扩展名冒充DTA；说明需要在工作副本中显式转换，或交付转换代码。实际运行不从磁盘随意挑数据。

入口的配置文件参数应给绝对路径。为兼容手工调用，配置内相对`data_path`、相对`--output-root`及相对`--ado-dir`统一按**配置文件所在目录**解析，`~`按用户目录展开；不依赖启动时cwd。AI命令仍优先全部使用绝对路径，避免宿主改变目录。没有输出时不要默认写进安装目录或只读技能目录。

JSON接口未开放任意代码、自由options、if/in、权重或数据清洗命令。这是包装器边界，不代表Stata或本技能完全不能协助这些研究；有这类任务时按原模型交付独立do或说明尚缺哪项执行支持，不删除设定后强行套JSON。

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
  "data_path": "/research/project/data/panel.dta",
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

上例为配置结构示意，路径和变量名不是用户真实数据；生成用户配置时必须替换为当前环境中的实际绝对路径（Windows使用其盘符路径），不能把示意路径直接用于执行。

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
