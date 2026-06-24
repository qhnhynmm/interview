import { Icon } from '../components/icons.jsx'
import { AGENTS, FLOW } from '../constants/home.js'

export default function Home({ onStart }) {
  return (
    <div className="page container">
      {/* Hero */}
      <section className="hero">
        <div>
          <span className="eyebrow">
            <Icon name="spark" size={14} /> Internal HR tool
          </span>
          <h1>
            Run smarter interviews with{' '}
            <span className="grad">InterviewAI Aurelia</span>
          </h1>
          <p className="hero__lede">
            Hand <b>Aurelia</b>, your AI hiring assistant, a CV, a job description
            and your special requests — and let four cooperating agents host a
            complete virtual interview and return a detailed evaluation report.
          </p>
          <div className="hero__actions">
            <button className="btn btn--primary" onClick={() => onStart('interview')}>
              <Icon name="video" size={18} /> Create an interview
            </button>
            <button className="btn btn--ghost" onClick={() => onStart('result')}>
              <Icon name="table" size={18} /> View results
            </button>
          </div>
          <div className="hero__stats">
            <div>
              <div className="num">4</div>
              <div className="lbl">Cooperating agents</div>
            </div>
            <div>
              <div className="num">1</div>
              <div className="lbl">Link to the candidate</div>
            </div>
            <div>
              <div className="num">100%</div>
              <div className="lbl">Auto-generated reports</div>
            </div>
          </div>
        </div>

        <div className="card flow">
          <div className="flow__title">How it works</div>
          {FLOW.map((s, i) => (
            <div className="flow-step" key={i}>
              <div className="flow-step__ix">{i + 1}</div>
              <div>
                <div className="flow-step__t">{s.t}</div>
                <div className="flow-step__d">{s.d}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Agents */}
      <section className="agents">
        <div className="section-head">
          <span className="eyebrow">
            <Icon name="route" size={14} /> The agent panel
          </span>
          <h1>Meet the team behind Aurelia</h1>
          <p>
            Every interview is run by four specialized agents, coordinated from a
            single plan so the whole panel stays consistent.
          </p>
        </div>
        <div className="agents__grid">
          {AGENTS.map((a) => (
            <div className="agent-card" key={a.name}>
              <div className="agent-card__icon">
                <Icon name={a.icon} size={22} />
              </div>
              <h3>{a.name}</h3>
              <p>{a.d}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
