// All source/target edges are supplied; this baseline does NOT infer relationships.
const ELK = require('elkjs');
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', async () => {
  try {
    const request = JSON.parse(input);
    const graph = {id:'root', layoutOptions:{
      'elk.algorithm':'layered', 'elk.direction':request.direction,
      'elk.padding':'[top=16,left=16,bottom=16,right=16]',
      'elk.spacing.nodeNode':'24', 'elk.layered.spacing.nodeNodeBetweenLayers':'24'
    },children:request.nodes.map(n=>({id:n.id,width:n.width,height:n.height})),
      edges:request.edges.map(e=>({id:e.id,sources:[e.source],targets:[e.target]}))};
    const result = await new ELK().layout(graph);
    process.stdout.write(JSON.stringify(result));
  } catch (e) { console.error(e.message); process.exitCode = 1; }
});
