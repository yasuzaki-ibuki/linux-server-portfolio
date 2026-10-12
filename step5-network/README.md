# Step 5:ネットワーク

サーバーのネットワーク設定の確認・変更から、通信の観察、2台構成、ファイアウォールの見直しまでを行う。

- A. NetworkManagerによるネットワーク設定の確認と変更
- B. tcpdumpによる通信の観察
- C. 仮想マシン2台構成(予定)
- D. firewalldの見直し(予定)

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



## B. tcpdumpによる通信の観察

### 観察① Nginx → アプリ(サーバー内部の通信)

```bash
sudo tcpdump -i lo -nn -A port 8003
```

- TCPの3ウェイハンドシェイク(`[S]` → `[S.]` → `[.]`)、データ送信(`[P.]`)、切断(`[F.]`)の流れを確認
- Nginxからアプリへのリクエストに、設定した `proxy_set_header`(X-Real-IP、X-Forwarded-For など)が付与されていることを確認
- HTTPは暗号化されていないため、リクエストやHTMLの中身がそのまま読めることを確認(Step 7でHTTPS化する理由)

### 観察② 本体PCのブラウザ → Nginx

```bash
sudo tcpdump -i enp0s3 -nn port 80
```

- 本体PCのブラウザからのアクセスが、サーバーからは送信元 10.0.2.2(VirtualBoxの仮想ルーター)として見えることを確認
- ポートフォワーディングでは、VirtualBoxがNAT(アドレス変換)をして転送していることを、実際のパケットで確認

### 観察③ DNSの問い合わせ

```bash
sudo tcpdump -i enp0s3 -nn port 53
```

- 名前解決のときに、DNSサーバー(192.168.3.1)の53番(UDP)へ、A(IPv4)とAAAA(IPv6)の問い合わせが送られていることを確認
- Aで確認した設定(/etc/resolv.conf)と、実際の通信が一致することを確認

### キャプチャの保存

```bash
sudo tcpdump -i lo -nn -c 30 -w /tmp/kintai.pcap port 8003   # 30パケットでファイルに保存
sudo tcpdump -nn -r /tmp/kintai.pcap                          # ファイルから読み込み
```

- キャプチャファイルには通信の中身が含まれるため、確認後に削除した

### 学んだこと

- 「設定を見る(ip / nmcli / resolv.conf)」と「通信を見る(tcpdump)」の両方で確かめることで、ネットワークの切り分けができる
- 見張る出入り口(-i)とフィルター(port)を正しく選ぶことが大事。サーバー内部の通信は lo、外部との通信は enp0s3 を通る
