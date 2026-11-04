// Exercise the actual template handlers without network calls or extra packages.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('templates/index.html', 'utf8');
function handler(name, next) {
    return source.slice(source.indexOf('function ' + name + '('), source.indexOf(next, source.indexOf('function ' + name + '(')));
}
function element() {
    return {
        value: '', style: {}, dataset: {}, options: [], children: [],
        add(option) { this.options.push(option); },
        querySelector(selector) {
            const match = selector.match(/option\[value="([^"]+)"\]/);
            return match ? this.options.find(option => option.value === match[1]) : null;
        },
        appendChild(child) { this.children.push(child); },
        scrollIntoView() {},
        setAttribute() {},
        remove() {},
        innerHTML: '',
    };
}
function setup() {
    const elements = new Map();
    const get = key => {
        if (!elements.has(key)) elements.set(key, element());
        return elements.get(key);
    };
    const pending = [];
    const doc = {
        getElementById: get,
        querySelector: get,
        querySelectorAll: () => [],
        createElement: element,
    };
    const $ = selector => {
        const el = typeof selector === 'string' ? get(selector) : selector;
        return {
            length: 1,
            val(value) { if (value === undefined) return el.value; el.value = value; return this; },
            trigger() { return this; },
            append(option) { el.options.push(option); el.value = option.value; return this; },
            empty() { el.options = []; el.value = ''; return this; },
            find() { return { each() {} }; },
            each() {},
            text(value) { el.text = value; return this; },
            html() { return el.text || ''; },
        };
    };
    const context = vm.createContext({
        document: doc, $, console, window: {}, setTimeout: () => {},
        Option: function(text, value) { return { textContent: text, value, dataset: {} }; },
        fetch(url) { return new Promise(resolve => pending.push({url, resolve})); },
        formatConfig: {
            mens_t20: {maxOvers: 20, maxBowlerOvers: 4, label: "Men's T20", gender: 'men'},
            womens_t20: {maxOvers: 20, maxBowlerOvers: 4, label: "Women's T20", gender: 'women'},
            mens_odi: {maxOvers: 50, maxBowlerOvers: 10, label: "Men's ODI", gender: 'men'},
            womens_odi: {maxOvers: 50, maxBowlerOvers: 10, label: "Women's ODI", gender: 'women'},
        },
        refreshPlayerDropdowns() {}, updateBatsmenToCome() {}, toggleTargetField() {},
        getBowlerOptions: () => '', getBatsmanOptions: () => '', getAllPlayerOptions: () => '',
        addBowlerRow() {},
    });
    vm.runInContext(`
        let currentFormat = 'mens_t20', currentGender = 'men';
        let liveListRequest = 0, matchDetailsRequest = 0;
        let bowlerOptions = '', batsmanOptions = '', allPlayerOptions = '';
        ${handler('updateFormat', 'function refreshPlayerDropdowns')}
        ${handler('fetchLiveMatches', 'function refreshLiveMatches')}
        ${handler('loadMatchData', 'function populateFormFromMatch')}
        ${handler('populateFormFromMatch', '$(document).ready')}
        ${handler('loadMatchFromCard', 'function saveFavTeam')}
    `, context);
    return {context, get, pending};
}
async function respond(request, body) {
    request.resolve({json: async () => body});
    await new Promise(resolve => setImmediate(resolve));
}
const sample = format => ({
    format, current_score: 151, wickets: 2, overs: 12.3, innings: 2, target: 301,
    venue: 'Test Ground', fielding_team: 'India', status: 'Live',
    batsmen: [{name: 'Batter A', runs: 70, balls: 50}, {name: 'Batter B', runs: 0, balls: 0}],
    bowlers: [{name: 'Bowler A', runs_conceded: 30, wickets: 2, overs_bowled: 3.2}],
    bowling_team_11: ['Bowler A', 'Bowler B'], last_over_bowler: 'Bowler A',
});
function click(s, id, format) {
    s.context.loadMatchFromCard({dataset: {
        matchId: id, matchFormat: format, matchLabel: 'NZ vs IND', matchStatus: 'Live',
    }});
}
(async () => {
    // Initially empty dropdown, manual mode, all four formats.
    for (const format of ['mens_t20', 'womens_t20', 'mens_odi', 'womens_odi']) {
        const s = setup();
        click(s, '123', format);
        assert.equal(s.get('liveMatchSelect').value, '123');
        assert.equal(s.get('mode_live').checked, true);
        assert.equal(s.get('input_mode_hidden').value, 'live');
        assert.equal(s.pending.length, 1); // No filtered list request to overwrite the selection.
        assert.equal(s.pending[0].url, '/api/live-match/123?format=' + format);
        await respond(s.pending[0], {success: true, match: sample(format)});
        assert.equal(s.get('match_format_hidden').value, format);
        assert.equal(s.get('live_match_id').value, '123');
        assert.equal(s.get('current_score').value, 151);
        assert.equal(s.get('wickets_fallen').value, 2);
        assert.equal(s.get('overs_completed').value, 12.3);
        assert.equal(s.get('target').value, 301);
        assert.equal(s.get('select[name="venue"]').value, 'Test Ground');
        assert.equal(s.get('fielding_team').value, 'India');
        assert.equal(s.get('select[name="batsman1_name"]').value, 'Batter A');
        assert.equal(s.get('input[name="batsman2_runs"]').value, 0);
        assert.equal(s.get('input[name="batsman2_balls"]').value, 0);
        assert.equal(s.get('bowlerRows').children.length, 1);
        assert.ok(s.get('bowlerRows').children[0].innerHTML.includes('Bowler A'));
        assert.equal(s.get('select[name="last_over_bowler"]').value, 'Bowler A');
        assert.ok(s.get('liveMatchStatus').innerHTML.includes('Click Predict'));
    }
    // Card selection supersedes an in-flight list request and a previous match fetch.
    const s = setup();
    s.context.fetchLiveMatches();
    click(s, 'old', 'mens_t20');
    click(s, 'new', 'womens_odi');
    await respond(s.pending[2], {success: true, match: sample('womens_odi')});
    await respond(s.pending[1], {success: true, match: {...sample('mens_t20'), current_score: 99}});
    await respond(s.pending[0], {success: true, matches: []});
    assert.equal(s.get('liveMatchSelect').value, 'new');
    assert.equal(s.get('live_match_id').value, 'new');
    assert.equal(s.get('current_score').value, 151);
    assert.equal(s.get('match_format_hidden').value, 'womens_odi');
    // Missing fields on a new match cannot retain the previous match's chase or score.
    click(s, 'partial', 'mens_odi');
    assert.equal(s.get('target').value, '');
    assert.equal(s.get('current_score').value, '');
    await respond(s.pending[3], {success: true, partial: true, loaded_fields: ['venue'], match: {venue: 'Other Ground'}});
    assert.ok(s.get('liveMatchStatus').innerHTML.includes('Please enter'));
    // Upstream errors remain visible, rather than silently leaving a blank form.
    click(s, 'error', 'mens_odi');
    await respond(s.pending[4], {success: false, error: 'Match unavailable'});
    assert.ok(s.get('liveMatchStatus').innerHTML.includes('Match unavailable'));
    click(s, 'upcoming', 'mens_odi');
    await respond(s.pending[5], {success: true, match: {venue: 'Other Ground', status: 'Upcoming'}});
    assert.ok(s.get('liveMatchStatus').innerHTML.includes('has not started'));
    // A stray target must not force a first-innings match into chase mode.
    s.context.populateFormFromMatch({...sample('mens_odi'), innings: 1, target: 270});
    assert.equal(s.get('innings').value, 1);
    assert.equal(s.get('target').value, '');
    console.log('Match-card autofill: all four formats, fields, races, partial/error/upcoming cases passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
