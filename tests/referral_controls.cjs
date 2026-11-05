const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const template = fs.readFileSync('templates/referrals.html', 'utf8');
const script = template.match(/<script>([\s\S]*?)<\/script>/)[1];
const link = 'https://example.test/r/test-referral-code';

function setup(navigator = {}, execCommand = () => false) {
  const callbacks = {};
  const elements = Object.fromEntries(
    ['referralLink', 'copyReferralLink', 'shareReferralLink', 'referralFeedback'].map(id => [id, {
      value: id === 'referralLink' ? link : '',
      textContent: '', classList: {remove() {}, add() {}},
      focus() {}, select() {this.selected = true}, setSelectionRange() {},
      addEventListener(event, handler) {callbacks[id] = handler},
    }])
  );
  vm.runInNewContext(script, {
    navigator,
    document: {getElementById: id => elements[id], execCommand},
  });
  return {elements, callbacks};
}

(async () => {
  let copied = null;
  let page = setup({clipboard: {writeText: async text => {copied = text}}});
  page.callbacks.copyReferralLink();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(copied, link);
  assert.match(page.elements.referralFeedback.textContent, /copied/);

  page = setup({}, () => true);
  page.callbacks.copyReferralLink();
  await new Promise(resolve => setImmediate(resolve));
  assert.match(page.elements.referralFeedback.textContent, /copied/);

  page = setup({clipboard: {writeText: async () => {throw new Error('Denied')}}});
  page.callbacks.copyReferralLink();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(page.elements.referralLink.selected, true);
  assert.match(page.elements.referralFeedback.textContent, /manually/);

  let shared = null;
  page = setup({share: async data => {shared = data}});
  await page.callbacks.shareReferralLink();
  assert.equal(shared.url, link);
  assert.match(page.elements.referralFeedback.textContent, /shared/);

  copied = null;
  page = setup({clipboard: {writeText: async text => {copied = text}}});
  await page.callbacks.shareReferralLink();
  assert.equal(copied, link);

  page = setup({share: async () => {throw {name: 'AbortError'}}});
  await page.callbacks.shareReferralLink();
  assert.match(page.elements.referralFeedback.textContent, /cancelled/);
  console.log('Referral Copy/Share: six scenarios passed');
})().catch(error => {console.error(error); process.exitCode = 1});
