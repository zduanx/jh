import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { format, parseISO, startOfMonth, endOfMonth, startOfWeek, endOfWeek, addDays, isSameMonth, isSameDay, addMonths, subMonths } from 'date-fns';
import './CalendarView.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Event type colors matching stage colors
const EVENT_COLORS = {
  applied: '#4338ca',     // indigo
  screening: '#b45309',   // amber
  interview: '#c2410c',   // orange
  reference: '#be185d',   // pink
  offer: '#047857',       // green
  accepted: '#065f46',    // dark green
  declined: '#475569',    // gray
  rejected: '#b91c1c',    // red
};

// Capitalize first letter of each word
const capitalizeCompany = (name) => {
  if (!name) return '';
  return name
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

// Get month key from date (YYYY-MM format)
const getMonthKey = (date) => format(date, 'yyyy-MM');

// Stage-specific field labels
const STAGE_FIELD_LABELS = {
  applied: {
    type: 'Application Type',
    referrer_name: 'Referrer',
    referrer_content: 'Referral Details',
  },
  screening: {
    type: 'Screening Type',
    with_person: 'With',
  },
  interview: {
    round: 'Round',
    type: 'Interview Type',
    interviewers: 'Interviewers',
  },
  reference: {
    contacts_provided: 'Contacts Provided',
  },
  offer: {
    amount: 'Offer Amount',
    intention: 'Intention',
  },
};

// Render stage-specific details
const renderStageDetails = (eventType, stageData) => {
  if (!stageData) return null;

  const labels = STAGE_FIELD_LABELS[eventType] || {};
  const details = [];

  Object.entries(labels).forEach(([key, label]) => {
    if (stageData[key]) {
      details.push({ label, value: stageData[key] });
    }
  });

  if (details.length === 0) return null;

  return (
    <div className="trk-cal-stage-details">
      {details.map(({ label, value }) => (
        <div key={label} className="trk-cal-stage-detail">
          <span className="trk-cal-stage-label">{label}:</span>
          <span className="trk-cal-stage-value">{value}</span>
        </div>
      ))}
    </div>
  );
};

/**
 * CalendarView - Calendar tab showing events across all tracked jobs.
 *
 * Features:
 * - Month grid view with events listed in each day cell (Apple Calendar style)
 * - Below calendar: Upcoming and Past events sections
 * - Month-based caching: tracks which months have been fetched
 * - Merges new events with existing cache (deduplicates by event ID)
 */
function CalendarView() {
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [events, setEvents] = useState([]);
  const [fetchedMonths, setFetchedMonths] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedCells, setExpandedCells] = useState(new Set()); // Track expanded day cells
  const [hoverCard, setHoverCard] = useState({ visible: false, event: null, x: 0, y: 0 });
  const [showCalendar, setShowCalendar] = useState(true); // Toggle calendar grid visibility

  // Track if initial fetch is done
  const initialFetchDone = useRef(false);

  // Fetch calendar events for specific months and merge with cache
  const fetchEvents = useCallback(async (start, end, isInitial = false) => {
    try {
      if (isInitial) {
        setLoading(true);
      }
      setError(null);

      const token = localStorage.getItem('access_token');
      let url = `${API_URL}/api/tracked/calendar/events`;
      if (start && end) {
        url += `?start=${start}&end=${end}`;
      }

      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch calendar events');
      }

      const data = await response.json();
      const newEvents = data.events || [];
      const newMonths = data.months || [];

      // Merge events: deduplicate by event ID
      setEvents((prevEvents) => {
        const eventMap = new Map();
        // Add existing events
        prevEvents.forEach((e) => eventMap.set(e.id, e));
        // Add/update with new events
        newEvents.forEach((e) => eventMap.set(e.id, e));
        return Array.from(eventMap.values());
      });

      // Mark these months as fetched
      setFetchedMonths((prev) => {
        const updated = new Set(prev);
        newMonths.forEach((m) => updated.add(m));
        return updated;
      });
    } catch (err) {
      setError(err.message);
    } finally {
      if (isInitial) {
        setLoading(false);
      }
    }
  }, []);

  // Initial fetch - no params, backend returns ±3 months aligned to month boundaries
  useEffect(() => {
    if (!initialFetchDone.current) {
      initialFetchDone.current = true;
      fetchEvents(null, null, true);
    }
  }, [fetchEvents]);

  // Check if current month has been fetched, if not fetch ±3 months around it
  useEffect(() => {
    const monthKey = getMonthKey(currentMonth);

    if (!fetchedMonths.has(monthKey) && initialFetchDone.current) {
      // Fetch ±3 months centered on current month (same as initial load)
      const rangeStart = subMonths(currentMonth, 3);
      const rangeEnd = addMonths(currentMonth, 3);
      const startDate = format(startOfMonth(rangeStart), 'yyyy-MM-dd');
      const endDate = format(endOfMonth(rangeEnd), 'yyyy-MM-dd');
      fetchEvents(startDate, endDate, false);
    }
  }, [currentMonth, fetchedMonths, fetchEvents]);

  // Group events by date
  const eventsByDate = useMemo(() => {
    const map = {};
    events.forEach((event) => {
      const dateKey = event.event_date;
      if (!map[dateKey]) {
        map[dateKey] = [];
      }
      map[dateKey].push(event);
    });
    // Sort events within each day by time
    Object.keys(map).forEach((key) => {
      map[key].sort((a, b) => {
        if (a.event_time && b.event_time) {
          return a.event_time.localeCompare(b.event_time);
        }
        return a.event_time ? -1 : 1;
      });
    });
    return map;
  }, [events]);

  // Separate upcoming and past events
  const { upcomingEvents, pastEvents } = useMemo(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const todayStr = format(today, 'yyyy-MM-dd');

    const upcoming = [];
    const past = [];

    events.forEach((event) => {
      if (event.event_date >= todayStr) {
        upcoming.push(event);
      } else {
        past.push(event);
      }
    });

    // Sort upcoming by date/time ascending
    upcoming.sort((a, b) => {
      const dateCompare = a.event_date.localeCompare(b.event_date);
      if (dateCompare !== 0) return dateCompare;
      if (a.event_time && b.event_time) {
        return a.event_time.localeCompare(b.event_time);
      }
      return 0;
    });

    // Sort past by date/time descending (most recent first)
    past.sort((a, b) => {
      const dateCompare = b.event_date.localeCompare(a.event_date);
      if (dateCompare !== 0) return dateCompare;
      if (a.event_time && b.event_time) {
        return b.event_time.localeCompare(a.event_time);
      }
      return 0;
    });

    return { upcomingEvents: upcoming, pastEvents: past };
  }, [events]);

  // Generate calendar grid days
  const calendarDays = useMemo(() => {
    const monthStart = startOfMonth(currentMonth);
    const monthEnd = endOfMonth(currentMonth);
    const startDate = startOfWeek(monthStart);
    const endDate = endOfWeek(monthEnd);

    const days = [];
    let day = startDate;

    while (day <= endDate) {
      days.push(day);
      day = addDays(day, 1);
    }

    return days;
  }, [currentMonth]);

  // Format time for display
  const formatTime = (timeStr) => {
    if (!timeStr) return '';
    const [hours, minutes] = timeStr.split(':');
    const hour = parseInt(hours, 10);
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const hour12 = hour % 12 || 12;
    return `${hour12}:${minutes} ${ampm}`;
  };

  // Format time short (for calendar cells)
  const formatTimeShort = (timeStr) => {
    if (!timeStr) return '';
    const [hours, minutes] = timeStr.split(':');
    const hour = parseInt(hours, 10);
    const ampm = hour >= 12 ? 'p' : 'a';
    const hour12 = hour % 12 || 12;
    return `${hour12}:${minutes}${ampm}`;
  };

  // Navigation handlers
  const goToPrevMonth = () => setCurrentMonth(subMonths(currentMonth, 1));
  const goToNextMonth = () => setCurrentMonth(addMonths(currentMonth, 1));
  const goToToday = () => setCurrentMonth(new Date());

  // Handle hover card positioning
  const handleEventMouseEnter = (e, event) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const cardWidth = 260;
    const cardHeight = 200; // Approximate height

    // Position to the right by default, flip to left if not enough space
    let x = rect.right + 8;
    if (x + cardWidth > window.innerWidth) {
      x = rect.left - cardWidth - 8;
    }

    // Position vertically centered, adjust if overflows
    let y = rect.top - 20;
    if (y + cardHeight > window.innerHeight) {
      y = window.innerHeight - cardHeight - 10;
    }
    if (y < 10) {
      y = 10;
    }

    setHoverCard({ visible: true, event, x, y });
  };

  const handleEventMouseLeave = () => {
    setHoverCard({ visible: false, event: null, x: 0, y: 0 });
  };

  // Render event item in calendar cell
  const renderCalendarEvent = (event) => (
    <div
      key={event.id}
      className="trk-cal-cell-event"
      style={{ borderLeftColor: EVENT_COLORS[event.event_type] || '#64748b' }}
      onMouseEnter={(e) => handleEventMouseEnter(e, event)}
      onMouseLeave={handleEventMouseLeave}
    >
      {event.event_time && (
        <span className="trk-cal-cell-event-time">{formatTimeShort(event.event_time)}</span>
      )}
      <span className="trk-cal-cell-event-title">
        {event.job.company_logo_url ? (
          <img
            src={event.job.company_logo_url}
            alt=""
            className="trk-cal-cell-logo"
          />
        ) : (
          <span className="trk-cal-cell-logo-placeholder">
            {event.job.company?.charAt(0).toUpperCase()}
          </span>
        )}
        {capitalizeCompany(event.job.company)}
      </span>
    </div>
  );

  // Render event card for lists below calendar
  const renderEventCard = (event) => (
    <div key={event.id} className="trk-cal-event-card">
      <div className="trk-cal-event-header">
        <span
          className="trk-cal-event-type"
          style={{ backgroundColor: EVENT_COLORS[event.event_type] || '#64748b' }}
        >
          {event.event_type}
        </span>
        <span className="trk-cal-event-datetime">
          {format(parseISO(event.event_date), 'EEE, MMM d')}
          {event.event_time && ` at ${formatTime(event.event_time)}`}
        </span>
      </div>
      <div className="trk-cal-event-job">
        <div className="trk-cal-event-company">
          {event.job.company_logo_url ? (
            <img
              src={event.job.company_logo_url}
              alt=""
              className="trk-cal-event-logo"
            />
          ) : (
            <span className="trk-cal-event-logo-placeholder">
              {event.job.company?.charAt(0).toUpperCase()}
            </span>
          )}
          <span>{capitalizeCompany(event.job.company)}</span>
        </div>
        <span className="trk-cal-event-title">{event.job.title || 'Untitled'}</span>
      </div>
      {event.location && (
        <div className="trk-cal-event-location">{event.location}</div>
      )}
      {renderStageDetails(event.event_type, event.note)}
      {event.note?.note && (
        <div className="trk-cal-event-note">{event.note.note}</div>
      )}
    </div>
  );

  if (loading && events.length === 0) {
    return (
      <div className="trk-cal-loading">
        <div className="trk-spinner"></div>
        <p>Loading calendar...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="trk-cal-error">
        <div className="trk-error-icon">⚠️</div>
        <h3>Error Loading Calendar</h3>
        <p>{error}</p>
        <button className="trk-retry-btn" onClick={() => fetchEvents(null, null, true)}>
          Try Again
        </button>
      </div>
    );
  }

  const today = new Date();

  return (
    <div className="trk-cal-container">
      {/* Calendar Grid */}
      <div className="trk-cal-grid-wrapper">
        {/* Calendar Header */}
        <div className="trk-cal-header">
          <div className="trk-cal-nav">
            <button className="trk-cal-nav-btn" onClick={goToPrevMonth}>
              ‹
            </button>
            <button className="trk-cal-nav-btn" onClick={goToNextMonth}>
              ›
            </button>
            <h2 className="trk-cal-month-title">
              {format(currentMonth, 'MMMM yyyy')}
            </h2>
          </div>
          <div className="trk-cal-header-right">
            <button className="trk-cal-today-btn" onClick={goToToday}>
              Today
            </button>
            <button
              className="trk-cal-toggle-btn"
              onClick={() => setShowCalendar(!showCalendar)}
              title={showCalendar ? 'Hide calendar' : 'Show calendar'}
            >
              {showCalendar ? '▲' : '▼'}
            </button>
          </div>
        </div>

        {/* Weekday Headers */}
        {showCalendar && (
          <div className="trk-cal-weekdays">
            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => (
              <div key={day} className="trk-cal-weekday">{day}</div>
            ))}
          </div>
        )}

        {/* Calendar Grid */}
        {showCalendar && (
          <div className="trk-cal-grid">
            {calendarDays.map((day) => {
              const dateKey = format(day, 'yyyy-MM-dd');
              const dayEvents = eventsByDate[dateKey] || [];
              const isCurrentMonth = isSameMonth(day, currentMonth);
              const isToday = isSameDay(day, today);
              const isExpanded = expandedCells.has(dateKey);
              const hasMore = dayEvents.length > 3;

              const toggleExpand = () => {
                setExpandedCells((prev) => {
                  const updated = new Set(prev);
                  if (updated.has(dateKey)) {
                    updated.delete(dateKey);
                  } else {
                    updated.add(dateKey);
                  }
                  return updated;
                });
              };

              return (
                <div
                  key={dateKey}
                  className={`trk-cal-cell ${!isCurrentMonth ? 'outside' : ''} ${isToday ? 'today' : ''} ${isExpanded ? 'expanded' : ''}`}
                >
                  <div className="trk-cal-cell-header">
                    <span className={`trk-cal-cell-date ${isToday ? 'today' : ''}`}>
                      {format(day, 'd')}
                    </span>
                  </div>
                  <div className="trk-cal-cell-events">
                    {(isExpanded ? dayEvents : dayEvents.slice(0, 3)).map(renderCalendarEvent)}
                    {hasMore && (
                      <div className="trk-cal-cell-more" onClick={toggleExpand}>
                        {isExpanded ? 'Show less' : `+${dayEvents.length - 3} more`}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Events Lists Below Calendar */}
      <div className="trk-cal-events-sections">
        {/* Upcoming Events */}
        <div className="trk-cal-events-section">
          <h3 className="trk-cal-section-title">
            Upcoming Events
            <span className="trk-cal-section-count">{upcomingEvents.length}</span>
          </h3>
          {upcomingEvents.length === 0 ? (
            <div className="trk-cal-no-events">
              <p>No upcoming events</p>
              <p className="trk-cal-hint">
                Add events from the Manage tab by expanding a job card
              </p>
            </div>
          ) : (
            <div className="trk-cal-events-list">
              {upcomingEvents.map(renderEventCard)}
            </div>
          )}
        </div>

        {/* Past Events */}
        <div className="trk-cal-events-section">
          <h3 className="trk-cal-section-title">
            Past Events
            <span className="trk-cal-section-count">{pastEvents.length}</span>
          </h3>
          {pastEvents.length === 0 ? (
            <div className="trk-cal-no-events">
              <p>No past events</p>
            </div>
          ) : (
            <div className="trk-cal-events-list">
              {pastEvents.map(renderEventCard)}
            </div>
          )}
        </div>
      </div>

      {/* Fixed Hover Card */}
      {hoverCard.visible && hoverCard.event && (
        <div
          className="trk-cal-hover-card visible"
          style={{ left: hoverCard.x, top: hoverCard.y }}
        >
          <div className="trk-cal-hover-header">
            <span
              className="trk-cal-hover-type"
              style={{ backgroundColor: EVENT_COLORS[hoverCard.event.event_type] || '#64748b' }}
            >
              {hoverCard.event.event_type}
            </span>
            <span className="trk-cal-hover-datetime">
              {hoverCard.event.event_time && formatTime(hoverCard.event.event_time)}
            </span>
          </div>
          <div className="trk-cal-hover-company">
            {hoverCard.event.job.company_logo_url ? (
              <img
                src={hoverCard.event.job.company_logo_url}
                alt=""
                className="trk-cal-hover-logo"
              />
            ) : (
              <span className="trk-cal-hover-logo-placeholder">
                {hoverCard.event.job.company?.charAt(0).toUpperCase()}
              </span>
            )}
            <span>{capitalizeCompany(hoverCard.event.job.company)}</span>
          </div>
          <div className="trk-cal-hover-title">{hoverCard.event.job.title || 'Untitled'}</div>
          {hoverCard.event.location && (
            <div className="trk-cal-hover-location">{hoverCard.event.location}</div>
          )}
          {renderStageDetails(hoverCard.event.event_type, hoverCard.event.note)}
          {hoverCard.event.note?.note && (
            <div className="trk-cal-hover-note">{hoverCard.event.note.note}</div>
          )}
        </div>
      )}
    </div>
  );
}

export default CalendarView;
