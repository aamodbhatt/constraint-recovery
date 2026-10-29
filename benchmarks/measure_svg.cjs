// Compatibility entry point; the browser bridge is packaged with the Python tool.
const bridge=require('../src/constraint_recovery/assets/browser_geometry.cjs');
module.exports=bridge;
if(require.main===module)bridge.main().catch(error=>{console.error(error.message);process.exit(1);});
