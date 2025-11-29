from bs4 import BeautifulSoup
import sys
import os

# ---------------------------------------------------------
# 1. 埋め込むためのクリーンなCSS定義
# ---------------------------------------------------------
CLEAN_CSS = """
  body {
    font-family: "Helvetica Neue", Arial, "Hiragino Kaku Gothic ProN", "Hiragino Sans", Meiryo, sans-serif;
    line-height: 1.6;
    color: #333;
    margin: 0;
    padding: 20px;
  }
  .container-responsive {
    width: 100%;
    margin-left: auto;
    margin-right: auto;
  }
  @media (min-width: 768px) { .container-responsive { width: 80%; } }
  @media (min-width: 1024px) { .container-responsive { width: 66.666%; } }

  h3.year-heading {
    font-size: 1.5rem;
    margin-top: 0.75rem;
    margin-bottom: 0.75rem;
    border-bottom: 2px solid #ddd;
    padding-bottom: 0.5rem;
  }

  details {
    border: 1px solid #ccc;
    border-radius: 4px;
    margin-bottom: 8px;
    background-color: #fff;
    overflow: hidden;
  }

  summary {
    font-weight: bold;
    padding: 1rem;
    cursor: pointer;
    background-color: #f9f9f9;
    list-style: none;
    position: relative;
    transition: background-color 0.2s;
  }
  summary:hover { background-color: #eee; }
  summary::-webkit-details-marker { display: none; }
  summary::after {
    content: "+";
    position: absolute;
    right: 1rem;
    font-weight: bold;
    transition: transform 0.2s;
  }
  details[open] summary::after { transform: rotate(45deg); }

  .details-content {
    display: grid;
    grid-template-rows: 0fr;
    transition: grid-template-rows 0.3s ease-out;
  }
  details[open] .details-content { grid-template-rows: 1fr; }
  .details-inner { overflow: hidden; }
  .content-padding {
    padding: 1rem;
    border-top: 1px solid #eee;
  }
  .summary-title { font-size: 1.25rem; margin: 0; }
  p { margin-top: 0; margin-bottom: 1rem; }
"""

def convert_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    # ---------------------------------------------------------
    # 2. 見出しタグ (h3) の変換
    #    Tailwindクラスがついたh3を探して書き換える
    # ---------------------------------------------------------
    # クラスに "text-2xl" を含む h3 をターゲットにする（緩い条件）
    for h3 in soup.find_all('h3', class_=lambda c: c and 'text-2xl' in c):
        # クラスを全削除して 'year-heading' のみにする
        h3['class'] = ['year-heading']
        # スタイル属性があれば削除（念のため）
        if h3.has_attr('style'):
            del h3['style']

    # ---------------------------------------------------------
    # 3. <sl-details> の変換
    # ---------------------------------------------------------
    # sl-details タグをすべて探す
    for sl_details in soup.find_all('sl-details'):
        # 新しい <details> タグを作成
        new_details = soup.new_tag('details')
        
        # --- Summary (タイトル) の処理 ---
        # slot="summary" を持つ要素を探す
        summary_slot = sl_details.find(attrs={"slot": "summary"})
        
        new_summary = soup.new_tag('summary')
        title_span = soup.new_tag('span', class_='summary-title')
        
        if summary_slot:
            # slotの中のテキストを取得して、新しいタイトルに入れる
            title_text = summary_slot.get_text(strip=True)
            title_span.string = title_text
            # 元のslot要素は削除（後で本文を取得するときに邪魔にならないように）
            summary_slot.decompose()
        else:
            title_span.string = "詳細" # フォールバック

        new_summary.append(title_span)
        new_details.append(new_summary)

        # --- Content (本文) の処理 ---
        # 残った中身をすべて移動するためのラッパー構造を作る
        # <div class="details-content"><div class="details-inner"><div class="content-padding">
        wrapper_content = soup.new_tag('div', class_='details-content')
        wrapper_inner = soup.new_tag('div', class_='details-inner')
        wrapper_padding = soup.new_tag('div', class_='content-padding')

        # sl-details の中身（decomposeしてない残り）をすべて移動
        # Move all children
        contents = [c for c in sl_details.contents if c.name or str(c).strip()]
        for content in contents:
            # Tailwindのクラスがついた <p> タグなどがあれば、クラスを掃除してもよいが
            # 今回は中身のテキスト構造はそのまま生かす方針
            wrapper_padding.append(content)

        wrapper_inner.append(wrapper_padding)
        wrapper_content.append(wrapper_inner)
        new_details.append(wrapper_content)

        # 元の <sl-details> を新しい <details> に置換
        sl_details.replace_with(new_details)

    # ---------------------------------------------------------
    # 4. 全体をラップするコンテナの処理
    # ---------------------------------------------------------
    # すでに container-responsive があればいいが、なければ全体をラップしたい
    # ここでは、bodyの中身を container-responsive でラップする処理を入れる
    
    # もし部分的なHTML片なら、divで囲んで返す
    if not soup.body:
        container = soup.new_tag('div', class_='container-responsive')
        # 全要素を移動
        contents = [c for c in soup.contents if c.name or str(c).strip()]
        for c in contents:
            container.append(c)
        
        # 完全なHTMLドキュメント構造を作成
        new_soup = BeautifulSoup("<!DOCTYPE html><html lang='ja'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>変換済みドキュメント</title></head><body></body></html>", 'html.parser')
        new_soup.head.append(new_soup.new_tag('style'))
        new_soup.head.style.string = CLEAN_CSS
        new_soup.body.append(container)
        return new_soup.prettify()

    else:
        # すでに完全なHTMLの場合、CSSを追加し、body直下をラップする
        style_tag = soup.new_tag('style')
        style_tag.string = CLEAN_CSS
        if soup.head:
            soup.head.append(style_tag)
        else:
            # headがない変なHTMLの場合
            head = soup.new_tag('head')
            head.append(style_tag)
            soup.html.insert(0, head)

        # bodyの中身を container-responsive でラップ
        container = soup.new_tag('div', class_='container-responsive')
        body_contents = [c for c in soup.body.contents if c.name or str(c).strip()]
        for c in body_contents:
            container.append(c)
        soup.body.clear() # 一旦空にして
        soup.body.append(container) # ラッパーを入れる

        return soup.prettify()

# ---------------------------------------------------------
# メイン処理
# ---------------------------------------------------------
if __name__ == "__main__":
    # ここに入力ファイル名を指定（なければ input.html）
    input_filename = "index.html" 
    
    # サンプルとして、あなたが提示したHTML片をデフォルトとして埋め込んでおきます
    # ファイルがあればそれを読み込みます
    if len(sys.argv) > 1:
        input_filename = sys.argv[1]

    sample_html = """
    <h3 class="w-full md:w-4/5 lg:w-2/3 mx-auto my-3 text-2xl">1987年</h3>

    <sl-details class="w-full md:w-4/5 lg:w-2/3 mx-auto">
      <div slot="summary" > <p class="text-xl">答申案発表</p></div>
      <p>　「総合政策学部」、「環境情報学部」という２学部の名称と、その理念が発表され、同日評議会で承認もされた。
      <br> 　総合政策については問題なかったが、環境情報については塾内外で当初はずいぶんと誤解を受けた。</p>
    </sl-details>
    """

    if os.path.exists(input_filename):
        with open(input_filename, "r", encoding="utf-8") as f:
            html_content = f.read()
            print(f"Loaded {input_filename}")
    else:
        print(f"File {input_filename} not found. Using sample content.")
        html_content = sample_html

    converted_html = convert_html(html_content)

    output_filename = "output_clean.html"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(converted_html)

    print(f"Conversion complete! Saved to {output_filename}")