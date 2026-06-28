# -*- coding: utf-8 -*-
"""Add 2 more Related Article cards + inline "קראו גם" box to each blog post."""

import re

BLOG_DIR = '../blog'

# Full card HTML for each post (keyed by short name)
CARDS = {
    'eich-ladaat': '''\n        <a class="blog-index-card" href="eich-ladaat-mishloach-hinam-amazon-israel.html">
          <img src="images/eich-ladaat.jpg" alt="איך לדעת אם מוצר מגיע חינם לישראל" class="blog-index-card__thumb" width="280" height="160" loading="lazy" />
          <div class="blog-card-body">
            <div class="blog-index-card__cat">🔍 בדיקה</div>
            <h3 class="blog-index-card__title">איך לדעת אם מוצר מגיע חינם לישראל</h3>
            <div class="blog-index-card__footer"><span class="blog-index-card__read">קריאה: ~5 דקות ←</span></div>
          </div>
        </a>''',
    'mekhs-umaam': '''\n        <a class="blog-index-card" href="mekhs-umaam-amazon-israel.html">
          <img src="images/mekhs-umaam.jpg" alt="מכס ומע&quot;מ על קניות מאמזון לישראל" class="blog-index-card__thumb" width="280" height="160" loading="lazy" />
          <div class="blog-card-body">
            <div class="blog-index-card__cat">💰 מסים</div>
            <h3 class="blog-index-card__title">מכס ומע&quot;מ על קניות מאמזון לישראל</h3>
            <div class="blog-index-card__footer"><span class="blog-index-card__read">קריאה: ~5 דקות ←</span></div>
          </div>
        </a>''',
    '10-tipim': '''\n        <a class="blog-index-card" href="10-tipim-lehisakhon-bamazon-israel.html">
          <img src="images/10-tipim.jpg" alt="10 טיפים לחיסכון באמזון לישראל (2026)" class="blog-index-card__thumb" width="280" height="160" loading="lazy" />
          <div class="blog-card-body">
            <div class="blog-index-card__cat">💡 טיפים</div>
            <h3 class="blog-index-card__title">10 טיפים לחיסכון באמזון לישראל (2026)</h3>
            <div class="blog-index-card__footer"><span class="blog-index-card__read">קריאה: ~5 דקות ←</span></div>
          </div>
        </a>''',
    'mishloach-hinam': '''\n        <a class="blog-index-card" href="mishloach-hinam-amazon-israel.html">
          <img src="images/mishloach-hinam.jpg" alt="משלוח חינם מאמזון לישראל: המדריך המלא" class="blog-index-card__thumb" width="280" height="160" loading="lazy" />
          <div class="blog-card-body">
            <div class="blog-index-card__cat">📦 משלוחים</div>
            <h3 class="blog-index-card__title">משלוח חינם מאמזון לישראל: המדריך המלא</h3>
            <div class="blog-index-card__footer"><span class="blog-index-card__read">קריאה: ~5 דקות ←</span></div>
          </div>
        </a>''',
    'amazon-prime': '''\n        <a class="blog-index-card" href="amazon-prime-mishloach-israel.html">
          <img src="images/amazon-prime.jpg" alt="מה זה Amazon Prime ואיך זה משפיע על משלוח לישראל" class="blog-index-card__thumb" width="280" height="160" loading="lazy" />
          <div class="blog-card-body">
            <div class="blog-index-card__cat">⭐ Prime</div>
            <h3 class="blog-index-card__title">מה זה Amazon Prime ואיך זה משפיע על משלוח לישראל</h3>
            <div class="blog-index-card__footer"><span class="blog-index-card__read">קריאה: ~5 דקות ←</span></div>
          </div>
        </a>''',
    'madrikh-kahniot': '''\n        <a class="blog-index-card" href="madrikh-kahniot-amazon-israel-2026.html">
          <img src="images/madrikh-kahniot.jpg" alt="מדריך מלא לקניות באמזון לישראל 2026" class="blog-index-card__thumb" width="280" height="160" loading="lazy" />
          <div class="blog-card-body">
            <div class="blog-index-card__cat">📖 מדריך מלא</div>
            <h3 class="blog-index-card__title">מדריך מלא לקניות באמזון לישראל 2026</h3>
            <div class="blog-index-card__footer"><span class="blog-index-card__read">קריאה: ~5 דקות ←</span></div>
          </div>
        </a>''',
    'bikorot-mezuyafot': '''\n        <a class="blog-index-card" href="bikorot-mezuyafot-amazon.html">
          <img src="images/bikorot-mezuyafot.jpg" alt="ביקורות מזויפות באמזון — איך לזהות ולהימנע" class="blog-index-card__thumb" width="280" height="160" loading="lazy" />
          <div class="blog-card-body">
            <div class="blog-index-card__cat">⚠️ ביקורות</div>
            <h3 class="blog-index-card__title">ביקורות מזויפות באמזון — איך לזהות ולהימנע</h3>
            <div class="blog-index-card__footer"><span class="blog-index-card__read">קריאה: ~5 דקות ←</span></div>
          </div>
        </a>''',
    'amazon-vs-aliexpress': '''\n        <a class="blog-index-card" href="amazon-vs-aliexpress-israel.html">
          <img src="images/aliexpress-vs-amazon.jpg" alt="אמזון מול AliExpress לישראל — מה עדיף לקנייה?" class="blog-index-card__thumb" width="280" height="160" loading="lazy" />
          <div class="blog-card-body">
            <div class="blog-index-card__cat">⚖️ השוואה</div>
            <h3 class="blog-index-card__title">אמזון מול AliExpress לישראל — מה עדיף לקנייה?</h3>
            <div class="blog-index-card__footer"><span class="blog-index-card__read">קריאה: ~5 דקות ←</span></div>
          </div>
        </a>''',
    'hacharot': '''\n        <a class="blog-index-card" href="hacharot-amazon-israel.html">
          <img src="images/hacharot.jpg" alt="החזרות מאמזון לישראל — איך מחזירים ומה מגיע לכם" class="blog-index-card__thumb" width="280" height="160" loading="lazy" />
          <div class="blog-card-body">
            <div class="blog-index-card__cat">↩️ החזרות</div>
            <h3 class="blog-index-card__title">החזרות מאמזון לישראל — איך מחזירים ומה מגיע לכם</h3>
            <div class="blog-index-card__footer"><span class="blog-index-card__read">קריאה: ~5 דקות ←</span></div>
          </div>
        </a>''',
    'hamutzarim': '''\n        <a class="blog-index-card" href="hamutzarim-hakhi-kedaim-laknot-bamazon-israel.html">
          <img src="images/hamutzarim.jpg" alt="המוצרים הכי כדאיים לקנות באמזון לישראל (2026)" class="blog-index-card__thumb" width="280" height="160" loading="lazy" />
          <div class="blog-card-body">
            <div class="blog-index-card__cat">🛒 מה לקנות</div>
            <h3 class="blog-index-card__title">המוצרים הכי כדאיים לקנות באמזון לישראל (2026)</h3>
            <div class="blog-index-card__footer"><span class="blog-index-card__read">קריאה: ~5 דקות ←</span></div>
          </div>
        </a>''',
    'mutzarim-asurim': '''\n        <a class="blog-index-card" href="mutzarim-asurim-yevu-israel.html">
          <img src="images/mutzarim-asurim.jpg" alt="מוצרים אסורים לייבוא לישראל מאמזון" class="blog-index-card__thumb" width="280" height="160" loading="lazy" />
          <div class="blog-card-body">
            <div class="blog-index-card__cat">🚫 ייבוא</div>
            <h3 class="blog-index-card__title">מוצרים אסורים לייבוא לישראל מאמזון</h3>
            <div class="blog-index-card__footer"><span class="blog-index-card__read">קריאה: ~5 דקות ←</span></div>
          </div>
        </a>''',
    'black-friday': '''\n        <a class="blog-index-card" href="black-friday-prime-day-israel.html">
          <img src="images/black-friday.jpg" alt="Black Friday ו-Prime Day לישראלים — מדריך חיסכון" class="blog-index-card__thumb" width="280" height="160" loading="lazy" />
          <div class="blog-card-body">
            <div class="blog-index-card__cat">🛍️ מבצעים</div>
            <h3 class="blog-index-card__title">Black Friday ו-Prime Day לישראלים — מדריך חיסכון</h3>
            <div class="blog-index-card__footer"><span class="blog-index-card__read">קריאה: ~5 דקות ←</span></div>
          </div>
        </a>''',
    'amazon-vs-ebay': '''\n        <a class="blog-index-card" href="amazon-vs-ebay-israel.html">
          <img src="images/amazon-vs-ebay.jpg" alt="אמזון מול eBay לישראל — מה עדיף לקנייה?" class="blog-index-card__thumb" width="280" height="160" loading="lazy" />
          <div class="blog-card-body">
            <div class="blog-index-card__cat">⚖️ השוואה</div>
            <h3 class="blog-index-card__title">אמזון מול eBay לישראל — מה עדיף לקנייה?</h3>
            <div class="blog-index-card__footer"><span class="blog-index-card__read">קריאה: ~5 דקות ←</span></div>
          </div>
        </a>''',
}

# Short display name for "קראו גם" inline links
SHORT_TITLE = {
    'eich-ladaat': ('eich-ladaat-mishloach-hinam-amazon-israel.html', 'איך לדעת אם מוצר מגיע חינם'),
    'mekhs-umaam': ('mekhs-umaam-amazon-israel.html', 'מכס ומע״מ על קניות מאמזון'),
    '10-tipim': ('10-tipim-lehisakhon-bamazon-israel.html', '10 טיפים לחיסכון באמזון'),
    'mishloach-hinam': ('mishloach-hinam-amazon-israel.html', 'משלוח חינם מאמזון: המדריך'),
    'amazon-prime': ('amazon-prime-mishloach-israel.html', 'Amazon Prime ומשלוח לישראל'),
    'madrikh-kahniot': ('madrikh-kahniot-amazon-israel-2026.html', 'מדריך מלא לקניות באמזון 2026'),
    'bikorot-mezuyafot': ('bikorot-mezuyafot-amazon.html', 'ביקורות מזויפות באמזון'),
    'amazon-vs-aliexpress': ('amazon-vs-aliexpress-israel.html', 'אמזון מול AliExpress'),
    'hacharot': ('hacharot-amazon-israel.html', 'החזרות מאמזון לישראל'),
    'hamutzarim': ('hamutzarim-hakhi-kedaim-laknot-bamazon-israel.html', 'המוצרים הכי כדאיים לקנות'),
    'mutzarim-asurim': ('mutzarim-asurim-yevu-israel.html', 'מוצרים אסורים לייבוא'),
    'black-friday': ('black-friday-prime-day-israel.html', 'Black Friday ו-Prime Day'),
    'amazon-vs-ebay': ('amazon-vs-ebay-israel.html', 'אמזון מול eBay לישראל'),
}

# Per-file config: [new_card_1, new_card_2, read_also_link_1, read_also_link_2, read_also_link_3]
FILES = {
    'mishloach-hinam-amazon-israel.html': {
        'new_cards': ['amazon-prime', 'madrikh-kahniot'],
        'read_also': ['hacharot', 'bikorot-mezuyafot', 'amazon-vs-ebay'],
    },
    'eich-ladaat-mishloach-hinam-amazon-israel.html': {
        'new_cards': ['mekhs-umaam', 'bikorot-mezuyafot'],
        'read_also': ['hamutzarim', 'amazon-vs-ebay', 'black-friday'],
    },
    'hamutzarim-hakhi-kedaim-laknot-bamazon-israel.html': {
        'new_cards': ['amazon-vs-ebay', 'black-friday'],
        'read_also': ['mishloach-hinam', 'hacharot', 'madrikh-kahniot'],
    },
    'amazon-vs-ebay-israel.html': {
        'new_cards': ['bikorot-mezuyafot', 'madrikh-kahniot'],
        'read_also': ['mishloach-hinam', 'mekhs-umaam', 'black-friday'],
    },
    'mekhs-umaam-amazon-israel.html': {
        'new_cards': ['madrikh-kahniot', '10-tipim'],
        'read_also': ['hacharot', 'eich-ladaat', 'bikorot-mezuyafot'],
    },
    '10-tipim-lehisakhon-bamazon-israel.html': {
        'new_cards': ['hamutzarim', 'bikorot-mezuyafot'],
        'read_also': ['eich-ladaat', 'amazon-prime', 'madrikh-kahniot'],
    },
    'amazon-prime-mishloach-israel.html': {
        'new_cards': ['black-friday', 'madrikh-kahniot'],
        'read_also': ['hamutzarim', 'mekhs-umaam', 'amazon-vs-ebay'],
    },
    'madrikh-kahniot-amazon-israel-2026.html': {
        'new_cards': ['eich-ladaat', 'amazon-prime'],
        'read_also': ['hamutzarim', 'mutzarim-asurim', 'bikorot-mezuyafot'],
    },
    'hacharot-amazon-israel.html': {
        'new_cards': ['mutzarim-asurim', 'bikorot-mezuyafot'],
        'read_also': ['mekhs-umaam', '10-tipim', 'mishloach-hinam'],
    },
    'amazon-vs-aliexpress-israel.html': {
        'new_cards': ['amazon-vs-ebay', 'bikorot-mezuyafot'],
        'read_also': ['mishloach-hinam', '10-tipim', 'amazon-prime'],
    },
    'bikorot-mezuyafot-amazon.html': {
        'new_cards': ['hacharot', 'amazon-vs-ebay'],
        'read_also': ['mishloach-hinam', 'mekhs-umaam', 'mutzarim-asurim'],
    },
    'mutzarim-asurim-yevu-israel.html': {
        'new_cards': ['bikorot-mezuyafot', 'mishloach-hinam'],
        'read_also': ['mekhs-umaam', 'eich-ladaat', 'amazon-vs-ebay'],
    },
    'black-friday-prime-day-israel.html': {
        'new_cards': ['amazon-vs-ebay', 'madrikh-kahniot'],
        'read_also': ['hamutzarim', 'mekhs-umaam', 'mishloach-hinam'],
    },
}


def make_read_also_box(links):
    parts = []
    for key in links:
        href, title = SHORT_TITLE[key]
        parts.append(f'<a href="{href}">{title}</a>')
    joined = ' · \n          '.join(parts)
    return (
        '\n\n      <div style="border-right:4px solid #e08a00;padding:14px 18px;'
        'background:#fff8ee;margin:28px 0;border-radius:0 6px 6px 0;font-size:0.95rem;">'
        f'\n        <strong>📖 קראו גם:</strong> {joined}\n      </div>'
    )


def nth_section_close(content, n):
    """Return the index just after the n-th (0-based) </section> tag."""
    pos = 0
    for i in range(n + 1):
        idx = content.find('</section>', pos)
        if idx == -1:
            return -1
        pos = idx + len('</section>')
    return pos


def update_file(filepath, new_cards, read_also_keys):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Add "קראו גם" inline box after the 4th </section> (index 3)
    insert_pos = nth_section_close(content, 3)
    if insert_pos == -1:
        print(f'  WARN: could not find 4th </section> in {filepath}')
    else:
        box = make_read_also_box(read_also_keys)
        content = content[:insert_pos] + box + content[insert_pos:]

    # 2. Add 2 new Related Article cards after the last </a> in the blog-index-grid
    grid_pos = content.find('blog-index-grid')
    if grid_pos == -1:
        print(f'  WARN: no blog-index-grid in {filepath}')
    else:
        # Find the closing </section> of the related articles section
        next_section_close = content.find('</section>', grid_pos)
        if next_section_close == -1:
            print(f'  WARN: no </section> after grid in {filepath}')
        else:
            # Find the last </a> before that </section>
            last_a_close = content.rfind('</a>', grid_pos, next_section_close)
            if last_a_close == -1:
                print(f'  WARN: no </a> in grid section of {filepath}')
            else:
                insert_pos = last_a_close + len('</a>')
                new_card_html = ''.join(CARDS[k] for k in new_cards)
                content = content[:insert_pos] + new_card_html + content[insert_pos:]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


import os

os.chdir(BLOG_DIR)
for filename, cfg in FILES.items():
    print(f'Updating {filename}...')
    update_file(filename, cfg['new_cards'], cfg['read_also'])
    print(f'  Done.')

print('\nAll files updated.')
