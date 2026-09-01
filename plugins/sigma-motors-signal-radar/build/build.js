const fs=require('fs'), path=require('path');
const tpl=fs.readFileSync(path.join(__dirname,'template.html'),'utf8');
const data=fs.readFileSync(path.join(__dirname,'us-map-data.js'),'utf8');
if(!tpl.includes('/*__US_MAP_DATA__*/')) throw new Error('placeholder missing');
const out=tpl.replace('/*__US_MAP_DATA__*/', data.trimEnd());
const dest=process.argv[2];
fs.writeFileSync(dest,out);
console.log('wrote',dest,out.length,'bytes');
