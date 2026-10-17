# 発表ペーストラッカー ― extensions.libreoffice.org での公開手順

公開先: https://extensions.libreoffice.org/
公式の手順: [Using this site as an extension maintainer](https://extensions.libreoffice.org/en/home/using-this-site-as-an-extension-maintainer)

> サイトの画面や項目名は変わることがあります。食い違うときは上の公式手順を優先してください。

---

## 1. 公開前の準備

### 1.1 メタデータを確認する（`src/description.xml`）

| 項目 | 現在の値 | 確認すること |
|---|---|---|
| `identifier` | `jp.atmitani.impress.pacetracker` | **公開後は変えられません**（更新の判定に使われるため）。逆ドメイン形式で、ほかの拡張機能と重ならない値にします。変える場合は `src/pacetracker.py` の `EXTENSION_ID` と `src/Addons.xcu` の `service:` URL も一緒に変えます |
| `version` | `1.0.0` | リリースのたびに上げます（例: 1.0.1, 1.1.0） |
| `publisher` | `at.mitani`（リンク先は extensions サイトのトップ） | 公開する名前と、ホームページかソースリポジトリの URL に変えます |
| `LibreOffice-minimal-version` | 7.4 | 古い版にも対応させるなら、その版で動作確認してから下げます |
| ライセンス | Mozilla Public License 2.0。LibreOffice と同じライセンス（`src/registration/license.txt`、`LICENSE`） | サイトにも同じライセンスを登録します。ソースファイルの先頭には MPL 2.0 の告知文（Exhibit A）を入れています。ファイルを追加するときも入れてください |

`description.xml` は 1 文字目から `<?xml ...?>` で始めます。前に空白や空行があると、導入時に「XML declaration allowed only at the start of the document」というエラーになります。

### 1.2 ビルドとテスト

```powershell
cd C:\Users\atmit\home\2026\LibreOffice\Impress\Extension
python tools\build_oxt.py
```

`dist\PresentationPaceTracker-<version>.oxt` ができます。公開前に、次をクリーンな環境（新しいユーザープロファイル）で確認します。

- [ ] 拡張機能マネージャーから導入でき、ライセンス画面が出る
- [ ] **ツール > アドオン > 発表ペーストラッカー** から管理画面が開く
- [ ] 開始 → スライドショー下端に進捗バーが出て、カメとウサギが動く
- [ ] スライドを戻すとウサギだけが左に戻る
- [ ] リセットで両方がスタートに戻る
- [ ] アイコンのアップロードと「初期アイコン」が効く
- [ ] 管理画面の **言語** で「日本語」「English」「自動」を切り替えて、どれも表示が崩れない
- [ ] LibreOffice 本体の表示言語が日本語・英語のどちらでも、「自動」で正しい言語になる
- [ ] できれば Linux / macOS でも確認する（`platform` は `all` で登録しているため）

新しいプロファイルで試すには、別の作業フォルダーを指定して起動します（フォルダーのパスは短めにします。長すぎると Windows のパス長制限で導入に失敗します）。

```powershell
& "C:\Program Files\LibreOffice\program\soffice.exe" "-env:UserInstallation=file:///C:/lotest"
```

### 1.3 掲載用の素材

| 素材 | ファイル |
|---|---|
| ロゴ | `src/icons/logo.png`（128×128） |
| スクリーンショット | `docs/images/screenshot_overlay.png`（進捗バー）、`docs/images/screenshot_dialog_en.png`（管理画面・英語。英語ページ用）、`docs/images/screenshot_dialog.png`（管理画面・日本語） |
| 利用手順 | `docs/INSTALL_en.md`（英語）、`docs/INSTALL_ja.md`（日本語）。ホームページやリポジトリに置いてリンクできます |
| 説明文（英語） | `src/description/desc_en.txt` をもとに書く |
| 説明文（日本語） | `src/description/desc_ja.txt` をもとに書く |
| ソースコードの URL | GitHub などで公開しておくと、サイトの「ホームページ / リポジトリ」欄に書けます |

英語の説明文の例:

> **Presentation Pace Tracker** shows a progress band at the bottom of the running Impress slide show. A turtle moves with the elapsed time and a rabbit moves with the slide progress, from a start flag to a goal flag. If the rabbit is ahead of the turtle you will finish on time. Set the planned duration, start/reset the measurement and upload your own icons from *Tools > Add-Ons > Presentation Pace Tracker*. The settings dialog is available in English and Japanese.

## 2. アカウントを作る

1. TDF のシングルサインオン（SSO）アカウントを https://user.documentfoundation.org/ で作ります。
2. https://extensions.libreoffice.org/admin にそのアカウントでログインします。

## 3. 拡張機能のページを作る

1. 左側の言語選択で **English** を選びます（英語が基本の言語で、ほかの言語の代わりにも表示されます）。
2. 緑の **Add Extension** ボタンを押します。
3. 項目を入力します。
   - タイトル: `Presentation Pace Tracker`
   - 説明: 1.3 の英語の説明文
   - タグ: `Impress`, `presentation`, `timer` など、合うものを少し
   - ホームページ / ソースリポジトリの URL
   - ロゴ・スクリーンショット（任意。ただし見つけてもらいやすくなります）
   - ライセンス: `MPL-2.0`（Mozilla Public License 2.0。`license.txt` と揃えます）
4. **create** を押して保存します。**ファイルは保存したあとでないと追加できません。**

## 4. リリース（.oxt）を追加する

1. 作ったページを下へスクロールし、リリースの欄で **Add Extension Release** を押します。
2. 入力フォームに記入して **Create** を押します。主な内容:
   - バージョン: `1.0.0`（`description.xml` と同じ）
   - 対応する LibreOffice のバージョン: 動作を確認した版（例: 26.8 と、確認できた古い版）
   - 対応 OS: 確認した OS（Python だけで書いているので、どの OS でも動く作りです）
   - ファイル: `dist\PresentationPaceTracker-1.0.0.oxt`
   - リリースノート: 例 `Initial release.`
3. フォームの項目はサイトの画面に合わせて入力してください（公式手順にも細かい項目の説明はありません）。

## 5. 日本語の説明を付ける（任意）

1. 左側の言語選択で **日本語** に切り替えます。
2. 紫の 2 文字アイコンが付いた項目だけを翻訳します。それ以外の項目は全言語で共通なので、ここで変えると英語版も変わります。
3. ラベルの色: 緑 = 英語の原文、灰色 = 英語で代用中、紫 = 翻訳済み。タグはモデレーターが翻訳します。

## 6. 公開を申請する

1. **publish** を押します。
2. ボランティアのモデレーターが確認してから公開されます。かかる日数は決まっていません。
3. 非公開（private）のままだと確認待ちの列に入りません。必ず publish してください。
4. 質問は [コミュニティフォーラムの Extensions カテゴリ](https://community.documentfoundation.org/c/extensions/36) へ。

## 7. 新しいバージョンを出すとき

1. `src/description.xml` の `version` を上げます（例: `1.0.1`）。
2. `python tools\build_oxt.py` で作り直し、テストします。
3. サイトの拡張機能ページで **Add Extension Release** から新しい .oxt を追加し、もう一度 publish します。
4. 1 年以上リリースがないと、サイトに「古い」という表示が出ます。新しい LibreOffice で動作を確認したら、リリースの対応バージョンに追加して出し直すと消えます。

## 8. 公開されているファイルの構成

```
PresentationPaceTracker-1.0.0.oxt
├── META-INF/manifest.xml      … 中身の登録（Python コンポーネント、メニュー定義）
├── description.xml            … ID・バージョン・名前・ライセンス・対応バージョン
├── description/desc_en.txt, desc_ja.txt
├── registration/license.txt   … Mozilla Public License 2.0（導入時に表示）
├── Addons.xcu                 … ツール > アドオン メニューとツールバーのボタン
├── pacetracker.py             … 本体（管理画面、計測、進捗バー）
└── icons/                     … カメ・ウサギ・旗のアイコン、ロゴ、ツールバー用アイコン
```
