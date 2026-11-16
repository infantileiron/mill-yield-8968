/** @typedef {{id:number,code:string,line:string,supplier:string,tonnes:number,received_date:string,samples:number}} Batch */
/** @typedef {{sample_code:string,batch_id:number,flour_yield:number,moisture:number,inspector:string}} Inspection */
/** @typedef {{id:number,title:string,line:string,status:string,result:object,note:string,source:'ledger'|'center',source_meta:object}} Review */
/** @typedef {{id:number,status:string,phase:string,batches_copied:number,inspections_copied:number,checkpoint_batch:number,checkpoint_inspection:number,error:string}} SyncRun */
/** @typedef {{id:number,kind:string,status:string,summary:object,details:Array<object>}} ReconcileReport */
export const API_VERSION='1';
