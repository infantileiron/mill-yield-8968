import {statuses,syncStatuses,centerStatuses} from '../../constants/enums.js';
import {esc} from '../../utils/format.js';
export const badge=status=>`<span class="badge ${esc(status)}">${esc(statuses[status]||status)}</span>`;
export const sbadge=s=>`<span class="badge ${esc(s)}">${esc(syncStatuses[s]||s)}</span>`;
export const cbadge=s=>`<span class="badge ${esc(s)}">${esc(centerStatuses[s]||s)}</span>`;
