# 発表ペーストラッカー (Presentation Pace Tracker)

[English](README_en.md) | 日本語

LibreOffice Impress のスライドショー下端に進捗バーを表示し、**経過時間（カメ）** と **スライドの進み具合（ウサギ）** を、スタート旗からゴール旗へ動くアイコンで見せる拡張機能です。

![進捗バー](docs/images/screenshot_overlay.png)

## 機能

1. 管理画面で発表予定時間（分・秒）を設定
2. 管理画面の **開始** で経過時間とスライド進捗の計測を開始（スライドショーも同時に開始できます）。タイトルスライドを発表前から映しておく場合は、2 枚目の表示から計測を始めるモードも選べます
3. スライドショーの下端に進捗バーを表示
   - 左端にスタートの旗、右端にゴールの旗
   - 時間アイコンとスライドアイコンがスタートからゴールへ横に動く
   - スライドを戻すとスライドアイコンは左へ戻り、時間アイコンはそのまま進む
   - 中央の線の色でペースを表示（緑 = 予定どおり、オレンジ = やや遅れ、赤 = 遅れ）
   - 表示領域（開始位置 X・Y、幅、高さ）を管理画面で画面に対する % で指定可能。値は保存され、リセット後も保持
   - 表示先を「スライド（聴衆も見える）」と「発表者コンソールのみ」から切り替え可能。聴衆に進捗を見せたくないときは発表者コンソールだけに表示
4. 管理画面の **リセット** で経過時間とスライド進捗をリセット
5. 時間・スライド・スタート・ゴールの 4 つのアイコンを管理画面からアップロードして変更可能（初期アイコン: 時間 = カメ、スライド = ウサギ、スタート = 緑の旗、ゴール = チェッカーフラッグ）。4 つとも同じ大きさで表示
6. 管理画面の言語を「自動 / 日本語 / English」から切り替え可能（選んだ言語は保存）

## ドキュメント

| 内容 | 日本語 | English |
|---|---|---|
| 導入・利用手順 | [INSTALL_ja.md](docs/INSTALL_ja.md) | [INSTALL_en.md](docs/INSTALL_en.md) |

## フォルダー構成

```
VERSION              バージョン番号（ここだけで設定する）
src/                 拡張機能の中身（.oxt にそのまま入る）
  pacetracker.py     本体（Python UNO コンポーネント）
  Addons.xcu         メニュー・ツールバー
  description.xml    ID・バージョンなど（バージョンはビルド時に VERSION から書き込まれる）
  icons/             アイコン（.svg は元データで、.oxt には入れない）
tools/
  build_oxt.py       src/ から dist/*.oxt を作る
  gen_icons.py       アイコンの SVG を作る
  render_icons.py    SVG を LibreOffice で PNG にする
dist/                ビルドした .oxt
docs/                手順書とスクリーンショット
```

## ビルド

```powershell
python tools\build_oxt.py
```

バージョン番号は `VERSION` ファイル 1 か所で管理します。番号を変えてビルドすると、`src/description.xml` と .oxt のファイル名（`dist/PresentationPaceTracker-<version>.oxt`）に反映されます。

## ライセンス

[Mozilla Public License 2.0](LICENSE)（MPL-2.0）。LibreOffice と同じライセンスです。

This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0. If a copy of the MPL was not distributed with this file, You can obtain one at https://mozilla.org/MPL/2.0/.
