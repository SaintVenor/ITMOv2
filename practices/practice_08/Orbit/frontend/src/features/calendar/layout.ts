import type { CalendarItem } from '../../app/api';
import { intersects } from './dates';

const laneCount = 3;

interface Segment {
  item: CalendarItem;
  first: number;
  last: number;
  lane: number;
  continuesBefore: boolean;
  continuesAfter: boolean;
}

export function layoutWeek(days: string[], items: CalendarItem[]) {
  const segments: Segment[] = [];
  const occupied = Array.from({ length: laneCount }, () => new Array<boolean>(7).fill(false));
  const hidden = new Array<number>(7).fill(0);
  const firstSingleLane = new Array<number>(7).fill(0);
  const visible = items.filter(item => intersects(item, days[0], days[6]));
  const ordered = [
    ...visible.filter(item => item.startDate !== item.endDate),
    ...visible.filter(item => item.startDate === item.endDate),
  ];

  for (const item of ordered) {
    const continuesBefore = item.startDate < days[0];
    const continuesAfter = item.endDate > days[6];
    const first = continuesBefore ? 0 : days.indexOf(item.startDate);
    const last = continuesAfter ? 6 : days.indexOf(item.endDate);
    const multiDay = item.startDate !== item.endDate;
    const firstLane = multiDay ? 0 : firstSingleLane[first];
    const lane = occupied.findIndex((row, index) => index >= firstLane && !row.slice(first, last + 1).some(Boolean));
    if (lane === -1) {
      for (let col = first; col <= last; col += 1) hidden[col] += 1;
    } else {
      occupied[lane].fill(true, first, last + 1);
      if (multiDay) {
        for (let col = first; col <= last; col += 1) firstSingleLane[col] = Math.max(firstSingleLane[col], lane + 1);
      }
      segments.push({ item, first, last, lane, continuesBefore, continuesAfter });
    }
  }
  return { segments, hidden };
}
