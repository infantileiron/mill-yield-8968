export function route(){const page=location.hash.slice(1)||'batches';return ['batches','inspections','diagnosis','reports','sync'].includes(page)?page:'batches';}
