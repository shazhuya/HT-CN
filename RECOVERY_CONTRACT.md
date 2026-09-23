# HT-CN Stable Product Recovery Contract

本合同定义 Stable Product 的备份、恢复、更新、回滚和用户电脑调用边界。恢复流程不得改写 Source Truth、M4 37-component methodology、4-component Outcome Engine 或已消费的 prospective evidence。

## 恢复优先级

1. 先读取产品中文状态与 supervisor 子服务状态。
2. 普通子服务异常优先由 supervisor 自动重启和退避恢复。
3. 数据或产品状态异常先执行 `备份HT-CN.bat`，再使用产品化恢复路径。
4. release/update 异常必须先验证 release identity、package SHA-256 与备份清单，再允许替换 immutable release files。
5. 新 release 验证失败时必须**回滚** immutable release files，并保留 mutable data 与 pre-update backup。

## 备份合同

`备份HT-CN.bat` 生成带 SHA-256 inventory 的本地备份。权威 research/product state 纳入备份；可重建 cache/log 排除；私有原始行情不会上传到 release artifact。

## 恢复合同

`恢复HT-CN.bat` 必须在写入前验证备份 manifest，拒绝路径穿越、篡改或未知 future schema；恢复前创建 pre-restore snapshot；只恢复声明的 mutable product/research state，不修改 immutable release files。

## 更新与回滚合同

`更新HT-CN.bat` 只接受经过 release identity 与 package digest 验证的 pending package。流程为：pre-update backup → 停止服务 → staged replacement → 保留 mutable data → 验证新 release → 重启。任一 immutable verification 失败都必须回滚。

## 用户电脑边界

**用户电脑不是日常 CI、测试农场或 evidence 采集机。** 默认由 hosted CI、repository fixtures、agent-controlled runtime 和产品自身服务完成验证。

只有以下情形可以请求用户电脑：无法在托管环境重现的 Private-M1 特有故障、一次性私有数据迁移、用户主动要求的最终本地 UAT/预览、明确的本地兼容性故障。每次请求必须说明为什么自动化不能替代、唯一需要执行的动作、执行次数上限以及会产生什么唯一证据。

日常 M7 evidence accumulation、普通回归、QFQ/provider 测试、浏览器/图表回归、Project OS/freeze gate、等待更多样本天数，都不能成为调用用户电脑的理由。
