---
name: gehua-chen
description: 依据作者的OneClick 6.0帮助与源码，讲解命令、生成代码、诊断输出；可在本机Stata隔离运行原版，或用独立扩展保留全部回归规格及N、SE、实际p值和失败记录。用于明确询问OneClick、一键显著命令或其规格探索的任务；不自动用于所有Stata研究，不保证显著或将搜索结果当作独立验证。
---

# gehua Chen

将指定B站视频的主题整理成可复用的操作知识。知识细节已用作者6.0帮助与源码核对；没有完整音轨或字幕，不声称逐句还原视频，不虚构视频时间戳。来源与覆盖边界见 [sources.md](references/sources.md)。

## 按用户任务工作

- 讲解原理、命令参数或版本变化：读 [syntax.md](references/syntax.md)，有歧义时查 [implementation.md](references/implementation.md)。
- 写或修改代码：确认变量角色、估计器、样本、固定效应、标准误和输出位置；读 [workflow.md](references/workflow.md)，选用 [examples.md](references/examples.md) 的对应例子。未知项标为待填或询问，不从变量名猜研究设计。
- 解读结果或报错：读 [results-and-errors.md](references/results-and-errors.md)，核对本机实际安装文件和新产生的结果，不能用旧版本说明代替。
- 需要自动运行或保留全部规格：读 [execution.md](references/execution.md)，用`stata_runner.py plan/run`及类型明确的JSON配置。原版入口与`fullspec`扩展分开，使用用户授权的数据和新的运行目录。只有完成标记、结果核对均通过才称完成；没有可调用Stata时交付计划，不声称回归成功。

## 必须守住的操作事实

1. `oneclick y c1 c2, method(...) pvalue(...) fixvar(x ...)`：逗号前第一个变量是y，其余是候选控制变量；`fixvar()`第一项是受检验的x，其余固定保留。6.0语法要求至少两个候选控制变量。
2. 原版按实际双侧p值严格小于阈值筛选。默认输出仅含通过筛选的非空组合；`full`只将子集改成完整回归命令，**不导出全部规格**。结果列`p`是星号字符串，不能当数值p值。
3. `best`按记录的未调整R²排序取最后一行，存在缺失R²、不同样本等限制；不能解释为因果上或统计上最优。需要准确比较时单独重估并记录样本与诊断。
4. `threshold()`限制候选变量最低保留数量，不改变组合生成与中间观察数的指数级开销。运行前估算规模；可用 `python scripts/model_budget.py 8 --threshold 3`。只给预算，不在该脚本中运行回归。
5. 源码默认使用`save ..., replace`覆盖输出，并在工作数据中生成`subset direction coef p r2`。先检查字段冲突，使用新的输出目录和明确文件名。保留原始数据，不悄悄覆盖用户文件。
6. `method()`不是“任何估计器都兼容”的保证。检查目标系数可由`_b[]`/`_se[]`读取，分布、自由度与标准误适用。`zvalue`由用户明确设置；不凭命令名称一概判断。

## 分析与交付

忠实解释原命令可做的筛选，区分原版能力、源码静态推断、本次扩展和实际执行结果。不能把只输出显著组合称为全规格稳健性检验，也不能用筛选所得的普通p值直接宣称研究假设已获验证。用户需要完整探索记录时，采用本技能的`fullspec`循环，保留成功、失败和不显著规格；不要为“成功”自动改样本、控制项、标准误或阈值。

控制变量的合理性仍依据研究问题与识别设计；必要的混杂因素放在固定保留项，不能仅为结果好看随意删除。样本、估计器、固定效应、标准误等比较条件应明确；按需要保留完整规格记录。说明这一点即可，不用无关的道德说教替代用户的技术任务。

交付用户需要的解释或`.do`文件，同时说明版本、输入、输出、副作用及已验证范围。示例数值不是实测结果。诊断依赖数据时只给候选原因。外部回归命令的帮助与实际结果优先于泛化的示例。

## 资源

- [语法与参数](references/syntax.md)：详细角色、参数、分布、版本差异。
- [实际执行流程](references/workflow.md)：输入、检查、样本与运行后验证。
- [执行器与全规格扩展](references/execution.md)：JSON配置、隔离运行、输出字段、失败与完成判定。
- [代码示例](references/examples.md)：OLS、固定效应、聚类、z检验与重估。
- [结果与排错](references/results-and-errors.md)：字段、失败信号、常见误读。
- [实现审查](references/implementation.md)：源码定位与帮助不一致的地方。
- [能力分层](references/capabilities.md)：能交付到什么程度、还需什么条件。
- [来源登记](references/sources.md)：指定视频、作者来源、文件版本与校验值。
- [测试记录](references/tests/report.md)：维护时读取。
- [可运行配置](assets/fullspec_auto.json)：auto数据的4规格扩展演示，已在本机Stata实测。
- [原版教学do](assets/demo_auto.do)：适用于已有OneClick的空白会话；隔离执行优先使用上述执行器。
