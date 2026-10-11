# Step 5:ネットワーク

サーバーのネットワーク設定の確認・変更から、通信の観察、2台構成、ファイアウォールの見直しまでを行う。

- A. NetworkManagerによるネットワーク設定の確認と変更
- B. tcpdumpによる通信の観察(予定)
- E. 仮想マシン2台構成(予定)
- C. firewalldの見直し(予定)

## A. NetworkManagerによるネットワーク設定の確認と変更

### 現在の構成

```
VirtualBox NATネットワーク(10.0.2.0/24)
  rocky9-web(enp0s3:10.0.2.15/24)
     │
     ▼
  VirtualBoxの仮想ルーター(ゲートウェイ 10.0.2.2)
     │
     ▼
  本体PC(DNSは本体PCと同じ 192.168.3.1)→ インターネット

本体PCからの接続:ポートフォワーディング(127.0.0.1:2222 → 22、127.0.0.1:8080 → 80)
```

### 確認した内容

| 項目 | 値 | 確認したコマンド |
|---|---|---|
| IPアドレス | 10.0.2.15/24 | `ip -br address` |
| デフォルトゲートウェイ | 10.0.2.2 | `ip route` |
| DNSサーバー | 192.168.3.1(本体PCのDNSをVirtualBoxが引き渡し) | `cat /etc/resolv.conf` |
| 取得方法 | DHCP(ipv4.method: auto) | `nmcli -f ipv4 connection show enp0s3` |
| 設定ファイル | /etc/NetworkManager/system-connections/enp0s3.nmconnection | `ls` / `cat` |

### 学んだこと

- `ip` は「今の状態」、`nmcli` は「設定そのもの」を扱う
- DEVICE(機器)とCONNECTION(設定)は別物で、1つの機器に複数の設定を用意できる
- /etc/resolv.conf はNetworkManagerが自動生成するため、直接編集せず nmcli で変更する
- 疎通確認は「名前解決(getent hosts)」→「通信(curl)」の順に行い、DNSの問題か経路の問題かを切り分ける
- VirtualBoxのNATでは、DNSが仮想ルーター(10.0.2.3)ではなく本体PCのDNS(192.168.3.1)になる場合がある。標準値を思い込まず実機で確認した

### 設定の変更と切り戻し

DNSサーバーを手動指定に変更し、反映を確認したあと、元の設定に戻した。

```bash
# 変更(DHCPのDNSを使わず、指定したDNSを使う)
sudo nmcli connection modify enp0s3 ipv4.dns "1.1.1.1 8.8.8.8" ipv4.ignore-auto-dns yes
sudo nmcli device reapply enp0s3

# 確認
cat /etc/resolv.conf
getent hosts rockylinux.org

# 切り戻し
sudo nmcli connection modify enp0s3 ipv4.dns "" ipv4.ignore-auto-dns no
sudo nmcli device reapply enp0s3
```

- 反映には `nmcli device reapply` を使用(`connection up` と違い、接続を切らずに反映できるため、SSH接続中でも安全)
- 変更前に切り戻し手順を用意し、変更 → 確認 → 切り戻しの流れで作業した
