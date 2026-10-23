# OneClick 技能独立试用记录

交付整理说明：仅将本机绝对路径改为通用标识，试答内容未重写。教学do在本次试用后移除了`set more off`，下文保留试用时发现该设置未恢复的历史记录；没有做Stata实测。

日期：2026-10-23。任务约束：只读取技能目录及授权的原始 `oneclick.ado`；不联网、不执行 Stata、不修改技能。本记录仅写入指定的 `responses.md`，没有读取尚未编写的 `report.md`。

## 1. full、p 列与显著比例

不能直接计算。6.0 的 `full` 只是把通过筛选的组合文字 `subset` 换成完整命令 `command`，没有补回不显著或估计失败的规格。`p` 还是字符串星号，不是数值 p；恰好 .01、.05 等边界还可能无星号。因此既不能直接做 `p<.05`，也不能从星号反推精确 p。即使重估导出行得到数值 p，分母仍只是已经筛选的结果，不能代表所有规格的显著比例。若要报告全规格敏感性，应另外记录每个规格的返回码、精确 p、N、SE 与样本规则，保留不显著和失败规格；这属于扩展循环，原版文件没有提供。

依据：`references/syntax.md`、`references/results-and-errors.md`、`references/workflow.md`；原始 ado 的筛选、删除与 `full` 分支。

## 2. logit、best 与缺失 R²

`best` 不找最小 p。源码只对通过筛选的结果按记录的 `e(r2)` 排序，取最后一行再重估；它既不优化识别质量，也不比较完整模型池。缺少 `e(r2)` 时这个排序依据可能全缺失或不可用，不能把返回的一行称为最好模型，源码也不会自动换用其他拟合度指标。先单独运行实际 logit 基准式，用 `ereturn list` 查看返回量，核对目标系数和推断统计量；技能的 logit 示例明确设置 `zvalue`，但没有启用 `best`。若确需比较模型，须另定适用指标、共同样本及诊断规则。本次没有 Stata，以上是源码静态判断。

可交付而未执行的检查：

```stata
logit y x c1 c2
 ereturn list
 lincom x
```

这里的变量只是角色占位，不能当成已经跑出的模型。

依据：`references/examples.md`、`references/implementation.md`、`references/syntax.md`；原始 ado 的 `replace r2 = e(r2)`、`sort r2` 与末行选择。

## 3. 20 个候选与 threshold(19)

它显著减少回归调用数，但不能据此说总计算和内存都很小。阈值要求至少保留 19 个候选，所以候选回归数为 C(20,19)+C(20,20)=20+1=21；固定保留项不计入这 19 个。可是源码先生成全部 2^20=1,048,576 个组合，再把工作数据扩展到至少 1,048,576 行，之后才按阈值筛选回归。若原数据行数更多，则保留更多行；内存字节数及耗时还受变量类型、样本和估计器影响，不能由 21 推出。现有 JavaScript 工具已穷举全部子集，核对到 19 项 20 个、20 项 1 个；这是计数核验，不是 Stata 性能实测。

工具核验记录：

- 尝试 `python scripts/model_budget.py 20 --threshold 19`，但系统返回 Python 未找到、指向 Microsoft Store 的提示，脚本没有执行成功。
- 改用现有 `functions` JavaScript：遍历 `mask=0..2^20-1`，逐个数置位数，得到总组合 1,048,576、满足阈值 21。
- 父代理随后提供本机已有解释器 `<available-python-executable>`。使用该路径加 `-B` 成功运行原预算脚本，返回码 0，结果同为组合/最少工作行数 1,048,576、预计回归调用数 21，且 `executed_stata=false`。保留上述首次失败与独立穷举记录。
- 对照源码：默认不设阈值时，主循环含空组合，共 1,048,576 次候选回归调用；默认显示及非空组合上限是 1,048,575。设阈值 19 后两种有关回归的计数均为 21，不改变前面的组合生成与行数扩展。

依据：`scripts/model_budget.py`、`references/implementation.md`；原始 ado 的位图枚举、`set obs` 及阈值分支。

## 4. 无显著组与旧结果文件

不能凭目录里有 `oneclick_subset.dta` 就判定这次成功，更不能保证换一组控制变量后一定显著。源码在“显著组数为零”时先 `error 1` 退出，尚未走到保存步骤，因此旧文件可能原样留在目录里。应查本次日志、返回码、完整命令和文件修改时间，并为下一次使用新的专用输出名，确认新文件确由该次运行生成。还要区分没有组合通过阈值与估计失败、自由度或统计分布设置问题；没有真实日志不能断定原因。控制变量须依据研究设计确定，必要混杂项固定保留；修正程序错误也不等于保证存在显著效应。

依据：`references/results-and-errors.md`、`references/workflow.md`、`references/capabilities.md`；原始 ado 无显著组错误在保存分支之前。

## demo_auto.do 的输入输出保护静态检查

- 输入：脚本先检查 `c(N)` 或 `c(k)` 是否大于零，非空内存直接退出；随后才 `sysuse auto, clear`。因此它的保护方式是要求全新空会话，不是为任意现有数据自动备份。与文件头声明一致。示例使用四个实际变量建立共同完整样本；没有从用户数据推测研究设计。
- 输出：使用 `tempfile demo_result`，并把该路径显式传给 `saveplace()`。对照源码，非空 `saveplace` 会走指定路径保存分支；静态上避免默认 `oneclick_subset.dta` 的固定文件名覆盖，也没有删除已有用户字段或用户文件。
- 失败处理：`capture noisily` 后立即保存 `_rc`，只有返回零且 `confirm file` 成功才读取结果，其他路径给出检查提示；结束时 `clear`。全新 tempfile 也降低误读旧文件的风险。输出提示明确说明 `p` 是星号、结果经过筛选。
- 副作用和交付边界：示例会装载并清空演示数据，会设置 `more off`，且原 oneclick 会使用计时器 1；脚本没有恢复这些会话设置。需要长期保留结果时应另选明确输出路径，因为 tempfile 生命周期有限。脚本未检查本机包具体版本，运行前仍应按技能核对 `which` / `viewsource`。
- 当前结论：静态文本未见与所声明“空会话输入保护、临时结果输出”直接矛盾的地方；不能据此声称所有 Stata 路径、临时文件扩展名行为、语法或回归已经执行通过。没有执行 Stata，也没有安装软件。

## 实际阅读文件

技能根目录：`gehua-chen/`

1. `SKILL.md`
2. `references/syntax.md`
3. `references/implementation.md`
4. `references/results-and-errors.md`
5. `references/workflow.md`
6. `references/capabilities.md`
7. `references/examples.md`
8. `references/sources.md`
9. `assets/demo_auto.do`
10. `scripts/model_budget.py`

授权原始证据：`<inspected-author-source>/oneclick.ado`，只读全文。未读取原始 sthlp/pkg，未读测试 report、未联网。

## 本次发现与尚未覆盖的问题

1. 预算脚本只用标准库，逻辑与源码静态计数一致；本环境裸 `python` 命令不可用，但使用父代理提供的已有解释器绝对路径后实际运行成功。JavaScript 穷举也提供了独立数量核对；二者都是组合预算，未运行 Stata。
2. 技能能直接支持四题中的关键边界，并给出了找原始实现的定位。logit 的实际返回字段、缺失 R² 的具体排序表现、回归兼容性仍需本机 Stata 核验；不能凭阅读推定。
3. demo 的数据与固定文件名保护在静态上自洽；会话设置未恢复、包版本未自动断言、临时结果不用于长期交付，是使用范围及可改进项，未据此宣布执行失败。
4. 没有本次真实日志、数据或实际运行后的新文件，无法诊断第 4 题的具体故障，也未检查用户目录里的结果文件。
