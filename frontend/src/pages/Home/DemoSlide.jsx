export default function DemoSlide({ tab }) {
  if (tab === "Dashboard")
    return (
      <div className="ds-dashboard">
        <div className="ds-stats-row">
          <div className="ds-stat-card">
            <span className="ds-stat-num">24</span>
            <span className="ds-stat-lbl">Leads today</span>
          </div>
          <div className="ds-stat-card">
            <span className="ds-stat-num">8</span>
            <span className="ds-stat-lbl">Appointments</span>
          </div>
          <div className="ds-stat-card accent">
            <span className="ds-stat-num">96%</span>
            <span className="ds-stat-lbl">Response rate</span>
          </div>
        </div>
        <div className="ds-cols">
          <div className="ds-pipeline">
            <div className="ds-panel-title">Lead Pipeline</div>
            <div className="ds-lead">
              <span className="ds-dot green" />
              <span>Sarah Johnson</span>
              <span className="ds-tag hot">Hot</span>
            </div>
            <div className="ds-lead">
              <span className="ds-dot blue" />
              <span>Mike Chen</span>
              <span className="ds-tag warm">Warm</span>
            </div>
            <div className="ds-lead">
              <span className="ds-dot green" />
              <span>Emily Davis</span>
              <span className="ds-tag new">New</span>
            </div>
          </div>
          <div className="ds-activity">
            <div className="ds-panel-title">Recent Activity</div>
            <div className="ds-activity-item">
              <span className="ds-activity-dot" />
              New lead captured from website
            </div>
            <div className="ds-activity-item">
              <span className="ds-activity-dot" />
              Follow-up sent to Sarah Johnson
            </div>
            <div className="ds-activity-item">
              <span className="ds-activity-dot" />
              Appointment booked - Mike Chen
            </div>
          </div>
        </div>
      </div>
    );

  if (tab === "Widget Chat")
    return (
      <div className="ds-chat">
        <div className="ds-chat-window">
          <div className="ds-chat-header">
            <span className="ds-chat-status" />
            AI Assistant - Online
          </div>
          <div className="ds-chat-body">
            <div className="ds-msg bot">Hi! How can I help you today?</div>
            <div className="ds-msg user">
              I&apos;d like to schedule a consultation
            </div>
            <div className="ds-msg bot">
              Of course! I&apos;d be happy to help. What day works best for you?
            </div>
            <div className="ds-msg user">How about Thursday at 2pm?</div>
            <div className="ds-msg bot">
              Thursday at 2:00 PM is available. I&apos;ve booked that for you.
              You&apos;ll get a confirmation email shortly!
            </div>
          </div>
          <div className="ds-chat-input">
            <span>Type a message...</span>
          </div>
        </div>
      </div>
    );

  if (tab === "Clients")
    return (
      <div className="ds-clients">
        <div className="ds-panel-title">Clients &amp; Leads</div>
        <div className="ds-table">
          <div className="ds-table-head">
            <span>Name</span>
            <span>Score</span>
            <span>Stage</span>
            <span>Last Contact</span>
          </div>
          <div className="ds-table-row">
            <span>Sarah Johnson</span>
            <span className="ds-score high">92</span>
            <span className="ds-tag hot">Hot</span>
            <span>2 hrs ago</span>
          </div>
          <div className="ds-table-row">
            <span>Mike Chen</span>
            <span className="ds-score med">74</span>
            <span className="ds-tag warm">Warm</span>
            <span>1 day ago</span>
          </div>
          <div className="ds-table-row">
            <span>Emily Davis</span>
            <span className="ds-score high">88</span>
            <span className="ds-tag new">New</span>
            <span>Just now</span>
          </div>
          <div className="ds-table-row">
            <span>James Wilson</span>
            <span className="ds-score low">45</span>
            <span className="ds-tag cold">Cold</span>
            <span>5 days ago</span>
          </div>
          <div className="ds-table-row">
            <span>Lisa Park</span>
            <span className="ds-score med">67</span>
            <span className="ds-tag warm">Warm</span>
            <span>3 hrs ago</span>
          </div>
        </div>
      </div>
    );

  if (tab === "Automations")
    return (
      <div className="ds-automations">
        <div className="ds-panel-title">Email Sequence: New Lead Follow-Up</div>
        <div className="ds-sequence">
          <div className="ds-step active">
            <div className="ds-step-badge">1</div>
            <div className="ds-step-info">
              <strong>Welcome Email</strong>
              <span>Sent immediately</span>
            </div>
            <span className="ds-step-status sent">Sent</span>
          </div>
          <div className="ds-step-line" />
          <div className="ds-step active">
            <div className="ds-step-badge">2</div>
            <div className="ds-step-info">
              <strong>Case Study</strong>
              <span>After 2 days</span>
            </div>
            <span className="ds-step-status sent">Sent</span>
          </div>
          <div className="ds-step-line" />
          <div className="ds-step current">
            <div className="ds-step-badge pulse">3</div>
            <div className="ds-step-info">
              <strong>Check-In</strong>
              <span>After 5 days</span>
            </div>
            <span className="ds-step-status pending">Pending</span>
          </div>
          <div className="ds-step-line dim" />
          <div className="ds-step dim">
            <div className="ds-step-badge">4</div>
            <div className="ds-step-info">
              <strong>Special Offer</strong>
              <span>After 10 days</span>
            </div>
            <span className="ds-step-status">Scheduled</span>
          </div>
        </div>
      </div>
    );

  if (tab === "Calendar")
    return (
      <div className="ds-calendar">
        <div className="ds-panel-title">This Week - March 2026</div>
        <div className="ds-cal-grid">
          {["Mon", "Tue", "Wed", "Thu", "Fri"].map((day) => (
            <div className="ds-cal-col" key={day}>
              <div className="ds-cal-day">{day}</div>
              <div className="ds-cal-slots">
                {day === "Mon" && (
                  <>
                    <div className="ds-cal-event blue">9:00 - Sarah J.</div>
                    <div className="ds-cal-event green">2:00 - Mike C.</div>
                  </>
                )}
                {day === "Tue" && (
                  <div className="ds-cal-event purple">10:30 - Emily D.</div>
                )}
                {day === "Wed" && (
                  <>
                    <div className="ds-cal-event blue">11:00 - James W.</div>
                    <div className="ds-cal-event green">3:30 - Lisa P.</div>
                  </>
                )}
                {day === "Thu" && (
                  <div className="ds-cal-event accent">2:00 - New Consult</div>
                )}
                {day === "Fri" && (
                  <div className="ds-cal-event blue">9:30 - Follow-up</div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    );

  return null;
}
