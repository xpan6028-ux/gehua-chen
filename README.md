# gehua Chen

一个帮你使用 **Stata OneClick 6.0** 和比较回归结果的 Codex Skill。技能调用名为 **`$gehua-chen`**，界面显示名为 **gehua Chen**。

你提供数据、研究问题和基准模型，它帮助写代码、调用本机Stata、整理结果，并解释不同控制变量组合下的变化。Stata原命令仍叫 `oneclick`；本项目不是OneClick作者的官方项目。

## 主要功能

- 解释OneClick的变量角色、参数、输出和版本差异。
- 根据明确的基准模型生成代码，配置固定效应、稳健/聚类标准误和样本策略。
- 在独立Stata会话中执行，保存命令计划、do文件、日志、DTA/CSV及完成状态，不写回输入数据。
- 用新增的 `fullspec` 模式记录所有计划规格，包括不显著、估计失败和目标系数被省略的情况。
- 记录目标系数、标准误、实际双侧p值、样本量、自由度、95%区间和失败状态。
- 在运行前检查组合预算，识别超时、未完成输出和变量名错误。

**两种模式要区分：** `oneclick` 调用作者原版，输出仍是筛选后的显著非空组合；`fullspec` 是本项目独立扩展，保留全部计划规格。原版的 `full` 选项只改输出形式，不等于全规格模式。

## 安装与调用

将本仓库完整放入 Codex 的技能目录，文件夹名为 `gehua-chen`。默认路径是 `~/.codex/skills/gehua-chen`；自定义 `CODEX_HOME` 时使用其 `skills` 目录。

Windows默认目录可用：

```powershell
git clone https://github.com/xpan6028-ux/gehua-chen.git "$env:USERPROFILE\.codex\skills\gehua-chen"
```

目标目录需尚不存在。安装后，在Codex中调用：

> 请使用 $gehua-chen，帮我检查这条基准回归，说明哪些变量固定保留、哪些作为候选，并生成全规格比较计划。

也可以提出具体任务：

> 请使用 $gehua-chen，用Stata自带auto数据，price为因变量，weight为受检验变量，mpg和rep78为候选控制变量，使用稳健标准误。保留全部规格，包括不显著和失败的规格，运行后解释结果。

本机开发安装已由旧名迁移为 `gehua-chen`，今后使用新调用名。通过Git克隆安装的副本，可以在该目录运行 `git pull --ff-only` 更新。

## 运行条件与教学示例

命令解释与代码生成不要求本机能启动Stata；**实际回归需要可调用、具有有效许可的Stata及相应估计命令**，本仓库不包含Stata、许可文件或第三方估计器。

执行器使用Python标准库，需要Python3.9+。Windows中的 `python` 可能是商店占位符，应使用真实解释器。以下命令中的 `python` 指已经确认可用的Python：

```powershell
python scripts/stata_runner.py plan assets/fullspec_auto.json --output-root ./runs
python scripts/stata_runner.py run assets/fullspec_auto.json --output-root ./runs
```

未指定Stata位置时会尝试查找，也可加 `--stata "实际Stata可执行文件路径"`。计划包含4个规格；每次执行创建独立目录。`plan`不运行Stata，`run`才启动回归。

`fullspec`不依赖OneClick安装。原版入口另外要求 `--ado-dir` 指向已核验的OneClick6.0源文件目录，版本由SHA-256核对；文件来源见[来源登记](references/sources.md)。执行器不会全局安装命令。

详细配置、模型预算、数据路径、样本政策、输出字段和完成判定见[执行说明](references/execution.md)。

## 已验证范围

Windows Stata18已实际运行验证：OLS、Logit、Probit、`xtreg, fe`、`reghdfe`和相应稳健/聚类标准误。28项测试通过，其中14项为实际启动Stata的集成测试；数据仅为auto与固定种子合成数据，未使用用户研究数据。更名后重新验证的记录见[测试报告](references/tests/report.md)。

无需Stata的测试：

```powershell
python references/tests/test_model_budget.py
python references/tests/test_stata_runner.py
```

实际Stata测试需设置 `STATA_EXE`；原版测试另需 `ONECLICK_ADO_DIR`，可用 `STATA_TEST_ROOT` 指定产物目录：

```powershell
python references/tests/test_stata_integration.py
```

## 使用边界与来源

- 控制变量是否应该纳入仍取决于研究问题和识别设计，不能仅凭显著性判断；本技能不保证显著或替代因果识别。
- 自动运行接口暂不支持任意估计器、权重、自由options、if/in或复杂交互/时序目标；xtreg RE和其他操作系统分支未经过本轮运行验收。
- 共同完整案例输入池不保证各估计器最终使用同一批观测；须检查实际样本字段。
- 尚未自动生成规格曲线和投稿用论文表格。
- 本项目依据指定[B站视频页面](https://www.bilibili.com/video/BV1b8BhYMEFx/)与作者正式帮助/源码整理，没有取得完整音轨转写，不能称为视频逐句复刻。

OneClick作者为Shutter Zor（左祥太）；正式软件见[作者网站](https://shutterzor.cn/stata/)及[SSC/RePEc条目](https://ideas.repec.org/c/boc/bocode/s459075.html)。原版软件的GPLv3说明与作者权利不因本技能名称而改变。本仓库不重新分发作者完整源码或帮助文件；新增执行器与原版软件的区别已在技能资料中注明。

## 文件入口

- [SKILL.md](SKILL.md)：技能指令与按需资料索引。
- [执行器](scripts/stata_runner.py)：计划、隔离执行和产物核验。
- [全规格收集器](assets/oc_collect.ado)：逐条估计及统计量/状态收集。
- [能力范围](references/capabilities.md)、[来源登记](references/sources.md)、[测试报告](references/tests/report.md)。
