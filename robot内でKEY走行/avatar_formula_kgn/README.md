# Avatar Robot OSS by Keigan
2023/10/27 初版 Keigan Inc.

# Requirement
- Windows 10/11 
- Python 3.9.X（推奨） / モータ－アップデートなければ 3.10, 11, 12 でも可
- Chrome ブラウザ

# 環境構築
- 電源ONでOS起動するようにBIOS設定変更（Keiganで済）
- PCのボタンシャットダウンを有効化
- avatar_formula_kgn ディレクトリを任意の場所にコピー
- ライブラリ類をインストール
- avatar_formula_kgn/main.py 内のソフト設定

## ライブラリ
- pyserial
- requests
- websocket-client
- nrfutil (モーターファームウェアアップデート時のみ python 3.9にインストールする。後述)


```bash
pip install pyserial
pip install requests
pip install websocket-client
```

※ websocket, websockets というライブラリがあるが、websocket-client とは異なる。インストールしないこと


その他実行エラーになる場合は必要なライブラリをインストールしてください

## main.py ソフト設定
main.py 内の設定を行う。

### CA（サイバネティックアバター）基盤のログイン情報
account_login() 関数内の以下URL引数を、ユーザーアカウントに応じて変更する。
- CAアカウント: hoge-ca001
- CAパスワード: hogehoge

の場合

```python
def account_login():
    # アカウント認証
    # name=, password の部分はアカウントに合わせて変更すること
    response = requests.post('https://api.avatarchallenge.ca-platform.org/clientLogin/?name=hoge-ca001&password=hogehoge')
    print(response.json())
    return response.json()
```


### ロボット
PC と ロボットのアクチュエータは、USB to RS485 により通信している。
main.py の以下のロボット初期化のところで、COMポートが正しいか確認する。
チップは CP2102 Silicon labs 製。デバイスマネージャ等で確認できる。

```python
robot = robot_4wd.Robot4WD("COM3")
```

# 使い方
- CA基盤URL: https://avatarchallenge.ca-platform.org/

## 操作者側
- CA基盤で OP（操作者）側としてログインしておく

テストではChromeの別ウィンドウでも良い

## ロボット側
- CA基盤で CA（ロボット）側としてログインしておく

CA基盤のログイン順序はどちらでも良い

最後に、ロボット側で main.py を実行する

```
cd path
python main.py
```

- OP（操作者）画面で、CA（ロボット）側のビデオ画像をクリックする
- 十字キー等インターフェイスが表示される
- 十字キーで、前進・後退、左旋回、右旋回 の遠隔操作が可能となる

### モーターのデバッグ方法
robot_4wd 内の以下関数のログのコメントアウトを解除する
```python
    # ログ情報callback
    def on_motor_log_cb(self, device_id, log):
        #モーターのレスポンスデバッグには、以下のコメントアウトを外してください
        #print("[ID:",device_id,'] log {} '.format(log))
```
これにより、以下のように4つのモーターからのレスポンスがログに反映される
```

```


# モーターファームウェアのアップデート
バグフィックスなど何らかの理由によりモータ―ファームウェアのアップデートが必要になった場合は、
モータードライバのマイコンをアップデートするため、nrfutil ライブラリが必要。
nrfutil 実行のためには、Python 3.9.X が必要。（3.10以降では subprocess に関するエラーが発生する）

## 手順
### python 3.9.X をインストールする
    - 非公式ダウンロードサイト: https://pythonlinks.python.jp/ja/index.html

### ライブラリのインストール
Python 3.9 にインストールする必要がある
Windows では Python ランチャーが使用できるため以下でOK
```
py -3.9 -m pip install nrfutil

```
上記でインストールしたパスをメモしておく

### start_dfu.py の編集
examples\windows\start_dfu.py の nrfutil のパス python39_nrfutil_path を上記のパスに変更する
```python
# Python3.9 の nrfutil パスを代入する。※ python 3.10 以降では マイコンアップデート用 nrfutil が非対応
python39_nrfutil_path = 'C:\\Users\\avater1\\AppData\\Local\\Programs\\Python\\Python39\\Scripts\\nrfutil.exe'
subprocess.run([python39_nrfutil_path, 'dfu', 'serial', '-pkg', 'firmware/pkg.zip', '-p', port, '-b', '115200', '-fc', '0'])
```

### アップデート実行
- /firmware ディレクトリに、新しいファームウェアデータの dfu.zip を格納する（Keiganから配布予定）
- start_dfu.py を実行する
```
cd examples\windows
python start_dfu.py
```
- アップデートしたいデバイス id を選択する
- キー[y] でアップデート開始


※ アップデート完了後は、非常停止スイッチによる必ず電源OFF を毎回行うこと。これを忘れると、別の id のアップデートが出来ない、別の id が正常に動作しないなどが起こる。
   id:1のアップデート→モーターの電源OFF/ON → id:2のアップデート → モーターの電源OFF/ON.... という順番となる

※ /firmware/dfu.zip が存在していることを確認すること


# リモートデスクトップ環境
Windows リモートデスクトップ環境を使用した場合、ロボット（ローカル）のカメラ映像、マイクが使えない問題について、
以下の有効化が必要。参考リンク参照のこと。
- リモートオーディオより、使用するマイク・スピーカーの設定
- ローカルデバイスとリソースより、使用するカメラの設定
- RemoteFX USB リダイレクトの有効化

## 参考リンク
- https://invisibletechnology.jp/rdp-camera/#toc6

# TIPS
Pythonを Windows App Store からインストールした場合に、証明書が古くなってしまう可能性がある。
cacert.pem の中身を、以下からダウンロードできる最新の証明書リストに置き換えると治る。

- http://curl.haxx.se/ca/cacert.pem
- https://mkcert.org/generate/
