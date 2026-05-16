# Cisco ACI MCP Server

Cisco ACI ファブリックの正常性確認を行う MCP (Model Context Protocol) サーバです。  
APIC REST API を通じてヘルス情報・フォルト情報を取得できます。

## 提供ツール

| ツール名 | 説明 |
|---|---|
| `get_fabric_health` | ファブリック全体のヘルススコア（0–100）|
| `get_pod_health` | ポッド単位のヘルス状態 |
| `get_node_list` | Spine/Leaf/APIC ノード一覧とヘルススコア |
| `get_node_health` | 特定ノードの詳細ヘルス情報 |
| `get_fault_summary` | アクティブフォルトを重大度別に集計 |
| `get_faults` | フォルト詳細一覧（重大度フィルタ・件数制限対応）|
| `get_tenant_health` | テナントごとのヘルススコア |
| `get_system_info` | ノードのシステム情報（稼働時間・バージョン等）|
| `get_apic_health` | APIC コントローラ自体のヘルス状態 |

## セットアップ

### 必要な環境変数

```bash
export ACI_HOST="apic.example.com"      # APIC の ホスト名 or IP
export ACI_USERNAME="admin"              # ユーザ名
export ACI_PASSWORD="your_password"      # パスワード
export ACI_VERIFY_SSL="true"            # SSL検証 (false で無効化)
```

### インストール

```bash
pip install -e .
```

### 起動

```bash
python -m cisco_aci_mcp
```

## Claude Code での設定

`~/.claude/mcp_servers.json` に追記します：

```json
{
  "mcpServers": {
    "cisco-aci": {
      "command": "python",
      "args": ["-m", "cisco_aci_mcp"],
      "env": {
        "ACI_HOST": "apic.example.com",
        "ACI_USERNAME": "admin",
        "ACI_PASSWORD": "your_password",
        "ACI_VERIFY_SSL": "false"
      }
    }
  }
}
```

## 使用例

```
# ファブリック全体の健全性確認
get_fabric_health()

# クリティカルなフォルトを最大20件取得
get_faults(severity="critical", limit=20)

# ノード101の詳細確認
get_node_health(pod_id=1, node_id=101)
```

## ヘルススコアの目安

| スコア | 状態 |
|---|---|
| 90–100 | 健全 |
| 70–89 | 注意 |
| 0–69 | 警告 |
