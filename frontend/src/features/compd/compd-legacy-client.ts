// The TYPES compD's screens imported from compD's old `api/client.ts`, re-pointed at the
// `/api/v1/d/*` contract. compD's old request functions are not carried over: every screen now calls
// the server through `useCompdApi`.

import type { DCognitiveProfile, DInteractionEvent } from '@/src/features/compd/api/compd-types';

export type CognitiveProfile = DCognitiveProfile;

/** One answered question as the quiz records it -- exactly the contract's event, nothing more. */
export type InteractionEvent = DInteractionEvent;
