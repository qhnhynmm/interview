// Home page: the end-to-end flow steps and the four-agent panel.

export const FLOW = [
  {
    t: 'HR submits inputs',
    d: 'Upload the candidate CV, the JD, and any special requests.',
  },
  {
    t: 'Aurelia plans the interview',
    d: 'The Planning Agent builds a tailored plan for the other agents.',
  },
  {
    t: 'Candidate gets a link',
    d: 'A meeting link with a specific date & time is generated.',
  },
  {
    t: 'Detailed report',
    d: 'After the session, a full evaluation report is produced.',
  },
]

export const AGENTS = [
  {
    icon: 'route',
    name: 'Planning Agent',
    d: 'Reads the CV, JD and requests, then orchestrates a tailored plan for the whole panel.',
  },
  {
    icon: 'chat',
    name: 'Interview Agent',
    d: 'Conducts the live virtual interview with role-specific and behavioral questions.',
  },
  {
    icon: 'code',
    name: 'Code Assignment Agent',
    d: 'Designs and supervises a coding task that fits the candidate level and the role.',
  },
  {
    icon: 'shield',
    name: 'Inspector Agent',
    d: 'Observes and scores performance against the plan, flagging signals for HR.',
  },
]
