import { json, request, type Area } from '../../app/api';

export type Motif = 'film' | 'route' | 'grid';

export interface PlanFields {
  title: string;
  area: Area;
  note: string;
  cover?: string | null;
}

interface Plan extends PlanFields {
  id: string;
  motif: Motif;
}

export interface PlanCard extends Plan {
  steps: Pick<Step, 'title' | 'done'>[];
}

export interface StepFields {
  title: string;
  scheduledDate: string | null;
  done: boolean;
}

export interface Step extends StepFields {
  id: string;
  planId: string;
  position: number;
}

export interface AvailableStep extends Step {
  planTitle: string;
  area: Area;
}

export interface ResourceFields {
  title: string;
  url: string;
}

export interface Resource extends ResourceFields {
  id: string;
}

export interface PlanDetail extends Plan {
  steps: Step[];
  resources: Resource[];
}

function planPath(id: string) {
  return '/plans/' + encodeURIComponent(id);
}

export const planApi = {
  list(signal: AbortSignal) {
    return request<{ items: PlanCard[] }>('/plans', { signal });
  },
  detail(id: string, signal: AbortSignal) {
    return request<PlanDetail>(planPath(id), { signal });
  },
  create(id: string, fields: PlanFields) {
    return request<PlanDetail>('/plans', json('POST', { id, ...fields }));
  },
  edit(id: string, fields: PlanFields) {
    return request<PlanDetail>(planPath(id), json('PATCH', fields));
  },
  removePlan(id: string) {
    return request<void>(planPath(id), { method: 'DELETE' });
  },
  removeStep(id: string) {
    return request<void>('/steps/' + encodeURIComponent(id), { method: 'DELETE' });
  },
  reorder(planId: string, ids: string[]) {
    return request<PlanDetail>(planPath(planId) + '/steps/order', json('PUT', { ids }));
  },
  available(signal: AbortSignal) {
    return request<{ items: AvailableStep[] }>('/steps?unscheduled=true&done=false', { signal });
  },
  addStep(planId: string, id: string, fields: StepFields) {
    return request<Step>(planPath(planId) + '/steps', json('POST', { id, ...fields }));
  },
  editStep(id: string, fields: Partial<StepFields>) {
    return request<Step>('/steps/' + encodeURIComponent(id), json('PATCH', fields));
  },
  addResource(planId: string, id: string, fields: ResourceFields) {
    return request<Resource>(planPath(planId) + '/resources', json('POST', { id, ...fields }));
  },
  removeResource(id: string) {
    return request<void>('/resources/' + encodeURIComponent(id), { method: 'DELETE' });
  },
};
