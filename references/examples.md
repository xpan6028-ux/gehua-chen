# 命令示例与迁移方法

以下只展示**作者原版OneClick**的接口，不是fullspec指令，也不是当前任务的执行结果。普通组合比较先按[执行说明](execution.md)选fullspec，无需安装OneClick。下列示意中的变量名须替换，sysuse/clear仅在独立教学会话使用；不要为了讲解而运行或清空用户现有会话。

示例用Stata的tempfile生成绝对临时输出路径，不依赖cwd，也不覆盖固定同名结果。正式交付应改为用户项目中新建输出目录的绝对路径；临时文件不作持久产物。执行规范见[workflow.md](workflow.md)，原版教学文件见[demo_auto.do](../assets/demo_auto.do)。

## OLS：分清候选项与固定项

```stata
sysuse auto, clear
keep if !missing(price, weight, mpg, rep78)
tempfile result

oneclick price mpg rep78, method(regress) pvalue(.05) ///
    fixvar(weight) options(vce(robust)) threshold(1) ///
    full saveplace("`result'")
```

解释：price是y；weight是每次保留且被检验的x；mpg和rep78参与组合；至少保留1个候选。此例为了便于比较先限定共同完整样本，并不表示所有研究都应按整池变量做完整案例删除。

`full`只让筛选结果显示完整回归命令。不能把这个文件叫“全部模型结果”。还可能一个匹配结果也没有，需查看返回码，不承诺会输出显著组。

## 固定保留部分变量

```stata
tempfile result
oneclick y c1 c2 c3, method(regress) pvalue(.05) ///
    fixvar(x required_control i.year) ///
    options(vce(cluster firm_id)) threshold(2) ///
    saveplace("`result'")
```

此例中的名称是角色示意，须替换成用户真实变量。`required_control`与年份项始终保留，`threshold(2)`只计算c1、c2、c3。聚类维度应由研究设计确定，不能把firm_id这个示意名称当作普遍答案。

## xtreg固定效应

```stata
xtset firm_id year
tempfile result
oneclick y c1 c2 c3, method(xtreg) pvalue(.05) ///
    fixvar(x required_control i.year) ///
    options(fe vce(cluster firm_id)) threshold(2) ///
    full saveplace("`result'")
```

先检查面板键唯一性和基准回归。不要因为见到`xtreg`便自动加`zvalue`：固定效应与随机效应的推断结果应分别核对。

## reghdfe多维固定效应

```stata
tempfile result
oneclick y c1 c2 c3, method(reghdfe) pvalue(.05) ///
    fixvar(x required_control) ///
    options(absorb(firm_id year) vce(cluster firm_id)) ///
    threshold(2) full saveplace("`result'")
```

吸收项放到`options(absorb(...))`，避免把大量虚拟变量视为待筛候选。检查reghdfe和依赖包已安装；数据中需要的组内变异、自由度与聚类条件仍由实际模型决定。

## 使用z检验的例子

```stata
sysuse auto, clear
keep if !missing(foreign, weight, mpg, rep78)
tempfile result
oneclick foreign mpg rep78, method(logit) pvalue(.05) ///
    fixvar(weight) zvalue full saveplace("`result'")
```

logit/probit相关估计失败、完全预测或缺失拟合度需要按实际输出检查。`best`依赖源码所取的`e(r2)`，不能假定这些模型具有可用且合适的这一字段，所以此例不启用`best`。

## 单独重估与结果解释

对一条实际选中的规格，复制并检查完整命令后重新估计。例如：

```stata
regress price weight mpg, vce(robust)
ereturn list
lincom weight
```

由估计器输出核对实际系数、SE、N、统计量和精确p；不能拿示意命令假装该规格已被选中。若要批量重估所有保存的`command`，先核对来源、变量与允许的估计器，不能把任意表格字符串直接当可信代码执行。

## 用户提供基准式时

把基准式拆成y、x、必要控制项、候选项、估计器选项和样本规则。未说明哪些控制项可以变化时，先向用户核对这一项；不要把整条原式中的变量都自动转成待筛选池。
