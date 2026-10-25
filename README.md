# gehua Chen

帮助AI按用户给定的基准模型，组合候选控制变量、生成Stata代码、按条件运行回归并解释完整结果。技能名称为`gehua-chen`，在Codex中可用`$gehua-chen`调用。

例如，3个候选变量有8种组合，8个有256种。受检验变量和必须保留的控制项始终保留；候选组合可限制最少/最多数量。默认的`fullspec`模式逐条记录成功、不显著、估计失败和目标变量被省略的情况，输出系数、SE、实际p值、N及状态。

本技能也提供作者OneClick6.0的讲解、迁移和排错。只有用户明确要原版时才采用`oneclick`入口；原版按显著性筛选，原版`full`选项不等于完整记录模式。本项目不是OneClick作者的官方项目。

## 按需求使用，不把所有依赖混在一起

| 需求 | 需要什么 | 可以交付什么 |
| --- | --- | --- |
| 讲解、比较已有表格/日志 | 对应问题和材料即可 | 解释、核查依据及候选原因；不需要Python或Stata |
| 组合计数、计划、代码 | 已明确的变量角色和模型要求 | 组合计划或do；数据尚未提供也可先做。运行plan脚本仅需Python3.9+ |
| 实际运行 | 当前工具有文件/进程能力、实际数据、可调用Stata及相应估计器 | 新输出目录、代码、日志、DTA/CSV及核验状态 |

生成计划不要求Stata已安装，也不要求OneClick源码目录。fullspec的运行不依赖OneClick；原版包装器的run才需固定哈希的源码目录。仅要计划时不运行；已要求运行且条件齐备时，检查后继续，无需重复询问是否运行。

## 安装与工具适配

把本仓库完整放进当前AI工具支持的技能目录。**不同工具目录不同**；运行时应从工具读取本`SKILL.md`时给出的实际绝对位置定位资源，不能假定当前目录就是技能目录，也不能把Codex目录套给豆包或其他工具。只获得本文文字而没有技能文件时，可参考说明，但无法据此声称已安装脚本。

以下是**Windows上安装到Codex**的完整示例，目标目录需尚不存在。该代码块同时定义安装位置、入口及输出位置，生成教学计划，不运行Stata：

```powershell
$skillInstallBase = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
$skillRoot = [IO.Path]::GetFullPath((Join-Path $skillInstallBase 'skills/gehua-chen'))
if (Test-Path -LiteralPath $skillRoot) { throw '目标已存在，请使用已有目录，不要覆盖安装。' }
git clone https://github.com/xpan6028-ux/gehua-chen.git $skillRoot
if ($LASTEXITCODE -ne 0) { throw '下载未完成。' }
$demoEntry = Join-Path $skillRoot 'scripts/run_demo.ps1'
$demoOutput = [IO.Path]::GetFullPath((Join-Path $env:USERPROFILE 'gehua-chen-runs'))
& $demoEntry -Action plan -OutputRoot $demoOutput
```

PowerShell演示入口按自身位置寻找Python脚本和教学配置，因而不要求先cd到技能目录。它检查PATH上的Python3.9+；若当前工具提供另一个Python运行时，给`-PythonExe`传其已核验的绝对路径即可。没有可用Python时会明确退出，不自动安装。实际回归把Action改成run；必要时用Stata参数给实际可执行文件路径。其他系统或AI工具可直接使用Python入口，路径规则见[执行说明](references/execution.md)。

通过Git克隆安装的副本，可在其实际目录用`git -C`配合该绝对目录执行`pull --ff-only`更新。其他导入方式按其宿主管理方式更新，不把普通导入目录当作Git仓库。

## 直接提出任务

> 请使用gehua-chen。我有因变量y、核心变量x和候选a/b/c，今天只生成全部组合计划，数据以后再提供，不运行Stata。

> 请使用gehua-chen。按照我提供的基准回归运行候选控制变量组合，必须保留项、固定效应和标准误按原模型设置。保留所有计划规格，解释系数与样本量的变化，并给出本次代码、结果和日志位置。

> 请使用gehua-chen。使用Stata自带auto数据，price为y、weight为x、mpg和rep78为候选、稳健标准误，用完整记录模式实际运行并解释4种组合。

Codex中可用`$gehua-chen`选择技能；其他宿主以其实际技能选择方式为准，不保证同样的美元调用语法。

## 执行入口与文件

- [SKILL.md](SKILL.md)：用途、路由和前置条件。
- [stata_runner.py](scripts/stata_runner.py)：plan/run入口，内部资源按脚本自身位置解析。
- [run_demo.ps1](scripts/run_demo.ps1)：Windows教学入口，输出根目录必须是绝对路径。
- [fullspec_auto.json](assets/fullspec_auto.json)：4规格教学配置。
- [执行说明](references/execution.md)：配置字段、路径规则、依赖与停止条件。
- [能力范围](references/capabilities.md)、[来源登记](references/sources.md)、[测试报告](references/tests/report.md)。

AI生成实际命令时，应先核验Python、入口、JSON和输出位置，再填入真实绝对路径；不要把相对文件名、尚未定义的变量或示意路径原样交给shell。输入DTA、输出和ado目录的相对参数为兼容手工使用，统一相对配置文件目录；AI执行优先用绝对路径。

## 验证与边界

已在Windows Stata18使用auto与固定种子合成数据验证OLS、Logit/Probit、xtreg FE、reghdfe及稳健/聚类标准误。新增验证覆盖任意启动目录、迁移安装位置、无数据/无Stata的plan、原版plan不依赖ado，以及独立PowerShell演示入口。完整记录见[测试报告](references/tests/report.md)，不把这些结果当作其他宿主已适配或用户研究数据已验收。

无需Stata的测试入口：[组合预算](references/tests/test_model_budget.py)、[参数与结果检查](references/tests/test_stata_runner.py)、[路径与依赖分支](references/tests/test_portability.py)。AI测试时同样从技能实际根目录生成这些文件的绝对路径。原生Stata集成测试见[集成测试](references/tests/test_stata_integration.py)，需要显式设置STATA_EXE，原版场景另需ONECLICK_ADO_DIR；缺少它们时测试会跳过，跳过不能说成已通过原生回归验证。

JSON包装器暂不支持权重、任意options、if/in或复杂交互/时序目标；遇到这些要求可以按原模型另写do，而不是删掉设定强行套包装器。共同完整案例输入池也不保证所有估计器最终使用相同观测，应检查实际样本字段。变量合理性与因果识别仍依赖研究设计，不保证显著。xtreg RE和其他系统批处理尚未经过本轮验收。

OneClick作者为Shutter Zor（左祥太），来源为[作者网站](https://shutterzor.cn/stata/)与[SSC/RePEc条目](https://ideas.repec.org/c/boc/bocode/s459075.html)。原版软件的GPLv3声明不因本技能名称而改变。本仓库不重新分发作者完整源码或帮助；视频未取得完整转录，技能使用也不要求先下载或观看视频。
