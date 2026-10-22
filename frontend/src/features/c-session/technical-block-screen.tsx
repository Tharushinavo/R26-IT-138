// The neutral surface for a 409. Carries NO diagnostic distinction whatsoever --
// task_service.py:375 and :389 collapse the unsigned-parameter refusal, every LiveEngineCError,
// and a non-active session into one bare ConflictError, so the information genuinely is not on the
// wire. This component's own prop type is the structural proof: it takes no `reason`, `cause`, or
// `kind` prop, only an optional support code -- there is no channel through which a cause could
// vary what is rendered, so a 409 caused by one thing and a 409 caused by another render
// byte-identical copy.

import { NeutralMessageScreen } from '@/src/features/c-session/neutral-message-screen';

export type TechnicalBlockScreenProps = {
  supportCode: string | null;
  onExit: () => void;
};

export function TechnicalBlockScreen({ onExit, supportCode }: TechnicalBlockScreenProps) {
  return (
    <NeutralMessageScreen
      detail="Something changed on our end. Let's take another look in a little while."
      onExit={onExit}
      supportCode={supportCode}
      title="One moment"
    />
  );
}
