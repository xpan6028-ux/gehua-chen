# 来源、版本与覆盖登记

核验日期：2026-10-23。技能内容依据可核对的软件资料编写，未完整获得视频音轨/逐字字幕。没有把搜索结果、弹幕、评论或视频推荐当作命令行为证据。

## 指定视频

- [BV1b8BhYMEFx](https://www.bilibili.com/video/BV1b8BhYMEFx/)：“「oneclick6.0」Stata一键显著命令。重大更新、极限提速，超过200%的代码重构！”
- 发布者：拿铁一定要加冰；页面显示发布时间2024-11-25；时长640秒，P1，cid 26987990223。
- 已核验：视频标题、作者、简介、合集与播放页面；B站公开播放器接口未返回可取得的字幕。
- 未核验：完整口头讲解、逐秒画面/代码演示、宣传提速幅度的独立基准。不能写成“看完后逐句转录”，也没有编造视频时间定位。
- 原分享URL里的设备/会话等跟踪参数未收录到技能。

## 作者与正式软件来源

| 来源 | 本次确认内容 | 使用边界 |
| --- | --- | --- |
| [作者主页](https://shutterzor.cn/) | Shutter Zor / Xiangtai Zuo（左祥太）与上述B站账号互链 | 用于作者身份与来源关系 |
| [作者软件页](https://shutterzor.cn/stata/) | oneclick软件描述、SSC安装方式与作者仓库入口 | 不据简短描述推断全部实现 |
| [作者旧仓库](https://github.com/ShutterZor/StataOneClick) | 旧do文件；2025-07-16说明建议通过SSC取得正式包 | 旧文件和tuples依赖说明不当作6.0源码 |
| [SSC/RePEc条目](https://ideas.repec.org/c/boc/bocode/s459075.html) | 软件编号S459075，修订2024-11-24，作者Shutter Zor，正式文件与GPLv3声明 | 说明正式发布来源，不代表运行已经通过 |
| [官方oneclick.ado](http://fmwww.bc.edu/repec/bocode/o/oneclick.ado) | 全部程序已静态阅读：头部Version6、2024/11/21，含oneclick和oneclick5 | 本次实际行为解释的主要依据 |
| [官方oneclick.sthlp](http://fmwww.bc.edu/repec/bocode/o/oneclick.sthlp) | 全部帮助已阅读：23 November2024；语法、参数、示例、视频入口 | Results段存在旧说明，已与源码区分 |
| [官方oneclick.pkg](http://fmwww.bc.edu/repec/bocode/o/oneclick.pkg) | Distribution-Date20241124，RequiresStata14，两个分发文件 | 版本和依赖登记 |

本次通过发布条目提供的HTTP正式文件地址读取；HTTPS连接未成功，未关闭TLS验证或绕过登录。第一版仅核验公开程序文字；第二版已在隔离会话中实际执行所核验的OneClick6.0，见[测试记录](tests/report.md)。

原始文件校验值、字节数与覆盖状态保存在 [source-manifest.json](source-manifest.json)。原始帮助/源码仅用于读取核对，没有将它们整份重新分发到技能包；技能说明和示例为本次重新编写，不是视频逐字稿。

## 本次加入的分析与工具

[实现审查](implementation.md)来自对具体代码的静态分析；[工作流](workflow.md)、[排错路径](results-and-errors.md)、预算工具和教学脚本是本次设计。涉及研究识别、报告全部规格等内容，不宣称作者在视频中逐条说过，也不伪称原版已具备这些扩展。

同一视频主题可以用正式源码补齐操作细节，但这不等于视频全量还原。若后来提供字幕或视频文件，可逐段补对口头解释与实际演示，并保留当前软件来源区分。
