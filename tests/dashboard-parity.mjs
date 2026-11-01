import fs from 'node:fs';
import zlib from 'node:zlib';
import assert from 'node:assert/strict';
import {cohort,variable,relationship,wilson} from '../dashboard/engine.mjs';
const data=JSON.parse(zlib.gunzipSync(fs.readFileSync(process.argv[2])));
const fixtures=JSON.parse(fs.readFileSync(process.argv[3]));
for(const f of fixtures){const c=cohort(data,f.selected);assert.equal(c.n,f.n);assert.equal(c.positive,f.positive);
 for(const [id,expected] of Object.entries(f.numeric)){const v=variable(data,id,c);assert.equal(v.numeric.count,expected.count);if(expected.mean==null)assert.equal(v.numeric.mean,null);else assert.ok(Math.abs(v.numeric.mean-expected.mean)<=1e-7*Math.max(1,Math.abs(expected.mean)));}
 for(const id of Object.keys(data.variables)){const v=variable(data,id,c);assert.equal(v.groups.reduce((s,g)=>s+g.n,0),f.n);assert.equal(v.groups.reduce((s,g)=>s+g.positive,0),f.positive);}
 for(let i=0;i<data.pairs.length;i++){const p=relationship(data,i,c);assert.equal(p.cells.flat().reduce((s,g)=>s+g.n,0),f.n);assert.equal(p.cells.flat().reduce((s,g)=>s+g.positive,0),f.positive);}
}
assert.deepEqual(wilson(0,0),[null,null]);console.log(`Dashboard/Python parity passed: ${fixtures.length} cohort scenarios`);
