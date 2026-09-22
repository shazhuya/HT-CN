# HT-CN Stable v1.0.0 Recovery Contract

目标是“可恢复且可审计”，不是静默把错误掩盖成成功。

## 代码身份

开发 checkout：Git HEAD 可用时 Git 是最高优先级，dirty worktree 必须 fail closed，release manifest 不能洗白。

正式安装包：只有无可用 Git HEAD 时才使用 `HTCN_RELEASE_IDENTITY.json`。manifest fingerprint、protected file size/SHA-256、unexpected protected files、M4 37/37 与 Outcome 4/4 attestation 必须全部通过。失败时不得生成 authoritative M4 evidence。

## supervisor 恢复

子进程异常退出后进行有上限指数退避。重复失败达到 crash-loop 阈值后停止自动重启该服务，并把聚合状态置为 degraded 或 blocked。必须保留日志、last exit code/error、release identity 和现有数据，禁止删除证据或改 JSON 伪造恢复。

## 数据分类

可备份：`data/research/`、`data/product/` 和声明的 catalog state。普通备份不包括 rebuildable cache、日志、immutable release 文件、私有原始行情大文件或 credentials。release package 永远不得携带私有市场数据。

## 备份与 restore

备份必须带 schema、创建时间、source identity、文件 path/size/SHA-256 和 inventory fingerprint。路径穿越、未声明文件、缺失文件或哈希错误一律拒绝。

restore 顺序：验证 → pre-restore 快照 → staging → 仅允许的 mutable 路径 → 临时文件原子替换。restore 不得修改 immutable release identity 文件。

## update 与 rollback

更新顺序：验证 pending release → 验证当前安装 → pre-update 备份 → staging → 保存旧 immutable 文件 → 替换 → 验证新 release identity → 刷新依赖。任一步失败都回滚 immutable 文件。

## schema migration

migration 必须有版本、按注册顺序执行、幂等；未知未来 schema fail closed。

## provider / evidence 边界

M9.1 负责 provider retry/failover/health。网络或 provider 故障不得写假成功水位。运行故障需要修复；ISSUE-0066 证据不足不需要恢复动作，M8 保持禁用即可。

## 用户电脑例外

正常开发/验证不依赖用户电脑。只有 hosted 无法复现的私有 M1 故障、一次性私有迁移、用户主动本地预览/验收或本地兼容性故障才可请求本机动作，并必须说明 hosted 为什么不能替代、唯一动作、次数和独特证据。
