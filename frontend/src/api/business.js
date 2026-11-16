import {api,post,download} from './client.js';
export const batches={list:()=>api('/batches'),create:d=>post('/batches',d)};
export const inspections={list:()=>api('/inspections'),create:d=>post('/inspections',d)};
export const reviews={list:()=>api('/reviews'),get:id=>api('/reviews/'+id),create:d=>post('/reviews',d),approve:(id,note)=>post(`/reviews/${id}/approve`,{note}),download};
export const sync={status:()=>api('/sync/status'),run:()=>post('/sync/run',{}),reconcile:()=>post('/sync/reconcile',{}),repair:d=>post('/sync/repair',d)};
