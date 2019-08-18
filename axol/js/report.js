function xquery(xpath, parent)
{
    let results = [];
    let query = document.evaluate(xpath, parent || document,
                                  null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
    for (let i = 0, length = query.snapshotLength; i < length; ++i) {
        results.push(query.snapshotItem(i));
    }
    return results;
}

const doc = document;

function hide_user(user) {

    // TODO append hidden?

    const cc = doc.getElementById('blacklisted');
    const d = doc.createElement('div'); cc.appendChild(d);
    const node = doc.createTextNode(user); d.appendChild(node);

// TODO ugh, doesn't look like $x works in FF
    const items = xquery(`.//div[@class='item' and .//*[@user='${user}']]`);
    console.log(`${user}: hiding ${items.length} items`);

    // TODO just delete?
    items.forEach(el => { el.hidden = true; });
}


window.addEventListener('DOMContentLoaded', async (event) => {
    const aaa = xquery('//a[@class="blacklist"]');
    for (let aa of aaa) {
        aa.addEventListener('click', async(event) => {
            const target = event.target;

            const u = target.getAttribute('user');

            if (confirm(`hide ${u}?`)) {
                hide_user(u);
            }
        });
    }

/*
    const elem = document.getElementById('blacklist-edit');
    CodeMirror.fromTextArea(elem, {
         mode:  'js',
         lineNumbers: true,
    });

    const but = document.getElementById('blacklist-apply');
    but.addEventListener('click', async () => {
        const editor = document.querySelector('.CodeMirror').CodeMirror;
        const bl = editor.getValue().split(/\n/);
        for (let x of bl) {
            if (x.length > 0) {
                hide(x);
            }
        }
    });
    */
});
