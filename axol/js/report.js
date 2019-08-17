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

function hide(thing) {
// TODO ugh, doesn't look like $x works in FF
    const items = xquery(`.//div[@class='item' and .//a[text()='${thing}']]`);
    console.log(`${thing}: hiding ${items.length} items`);
    items.forEach(el => { el.hidden = true; });
}


window.addEventListener('DOMContentLoaded', async (event) => {
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
});
