import {batches,inspections,reviews,sync} from '../api/business.js';
export const state={user:null,batches:[],inspections:[],reviews:[],selected:null,sync:null,syncExpanded:null};
export async function refresh(){[state.batches,state.inspections,state.reviews,state.sync]=await Promise.all([batches.list(),inspections.list(),reviews.list(),sync.status()]);if(state.selected)state.selected=await reviews.get(state.selected.id);}
