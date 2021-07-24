# Auto-Rig Pro Migration Helper

## 概要

これは既存のボーン構成から [Auto-Rig Pro](https://blendermarket.com/products/auto-rig-pro) への移行を行うための補助アドオンです。
同種のものに Auto-Rig Pro 作者製作の [Quick Rig](https://blendermarket.com/products/auto-rig-pro-quick-rig) があります。


## 簡単な仕組みの説明

AutoRig Pro の Smart 機能を間接的に使用、その後調整することで既存アーマチュアの移行を行います。

1. 既存のボーンの Head, Neck, Shoulder ... などの位置から、自動でマーカー設定
2. そこから AutoRig Pro の Smart でアーマチュアを仮生成
3. 生成したボーンはマーカーからの自動生成なので、既存のアーマチュアからHumanoidのボーン位置などをコピー
4. Humanoid 以外のボーンをカスタムボーンとして既存のアーマチュアからコピー
    - ただし、Humanoidボーン同士の間にあるような補助ボーンはコピーされません


## Unity を使用した移行

このアドオンは Unity エディタ拡張の [ExportHumanoidRig](https://github.com/Taremin/ExportHumanoidRig) のJSONを利用してボーンの設定を行います。


### Unity で必要な作業

1. Unity に ExportHumanoidRig を導入する
2. アバターに Humanoid リグの設定を行い、 ExportHumanoidRig で JSON をエクスポートする


### Blender で必要な作業

1. 3Dビューの `ARP` タブに `Auto-Rig Pro Migration Helper` の項目があるので、その中から先程エクスポートしたJSONファイルを `Base Humanoid` に指定します。
2. `Auto-Rig Humanoid` は特に問題ない限りは `標準` を指定してください
  - Auto-Rig Pro のアップデートなどで `ReferenceBones` の対応がおかしい場合はアドオンフォルダ内の `ARP_ReferenceBones.json` を修正してください
3. `Auto-Rig Export` は特に問題ない限りは `標準` を指定してください
  - Auto-Rig Pro のアップデートなどでエクスポートされるボーンの対応がおかしい場合はアドオンフォルダ内の `ARP_ExportBones.json` を修正してください
4. `Base Armature` に既存のアーマチュアオブジェクトを指定してください
5. `Migrate` ボタンを押すと Auto-Rig Pro でリグが自動的に生成されます


## 注意

アーマチュアや対象メッシュのスケールや座標系がずれていると正確な移行ができません。
その場合、すべてのトランスフォームを適用してから実行してみてください。
その他アニメーションが含まれていたり等が原因でボーンの位置取得などが正確にできないことがあります。
また Humanoid ボーンの名前などは AutoRig Pro 基準のものになります。頂点グループも置き換えられるため注意してください。

既存のアーマチュアとは別物になるため、`コピーを保存` などで **バックアップを取ってから移行を試すのを推奨** します。

## ライセンス

[MIT](./LICENSE)
