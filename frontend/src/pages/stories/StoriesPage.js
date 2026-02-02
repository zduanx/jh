import React, { useState, useEffect, useCallback, useRef } from 'react';
import StoryCard from './StoryCard';
import './StoriesPage.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

/**
 * StoriesPage - Behavioral interview story management.
 *
 * Features:
 * - 1:3 column layout (question list : story cards)
 * - STAR format (Situation, Task, Action, Result)
 * - Click left nav to scroll to story card
 * - Overview section shows concatenated STAR fields
 */
function StoriesPage() {
  const [stories, setStories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeStoryId, setActiveStoryId] = useState(null);
  const [isCreating, setIsCreating] = useState(false);

  const cardRefs = useRef({});
  const rightPanelRef = useRef(null);

  // Fetch all stories - only on mount
  const fetchStories = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/api/stories`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch stories');
      }

      const data = await response.json();
      setStories(data.stories || []);

      // Set first story as active if exists
      if (data.stories?.length > 0) {
        setActiveStoryId(data.stories[0].id);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStories();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Scroll to story card when clicking question in left nav
  const scrollToCard = (storyId) => {
    setActiveStoryId(storyId);
    // Small delay to ensure DOM is ready
    setTimeout(() => {
      const cardEl = cardRefs.current[storyId];
      if (cardEl && rightPanelRef.current) {
        cardEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, 50);
  };

  // Create new story
  const handleCreateStory = async () => {
    try {
      setIsCreating(true);
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/api/stories`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          question: 'New question...',
          type: '',
          tags: [],
          situation: '',
          task: '',
          action: '',
          result: '',
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create story');
      }

      const newStory = await response.json();
      setStories(prev => [newStory, ...prev]);
      setActiveStoryId(newStory.id);

      // Scroll to top after short delay
      setTimeout(() => {
        if (rightPanelRef.current) {
          rightPanelRef.current.scrollTo({ top: 0, behavior: 'smooth' });
        }
      }, 100);
    } catch (err) {
      console.error('Error creating story:', err);
    } finally {
      setIsCreating(false);
    }
  };

  // Update story
  const handleUpdateStory = async (storyId, updates) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/api/stories/${storyId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(updates),
      });

      if (!response.ok) {
        throw new Error('Failed to update story');
      }

      const updatedStory = await response.json();
      setStories(prev =>
        prev.map(s => (s.id === storyId ? updatedStory : s))
      );
      return true;
    } catch (err) {
      console.error('Error updating story:', err);
      return false;
    }
  };

  // Delete story
  const handleDeleteStory = async (storyId) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_URL}/api/stories/${storyId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to delete story');
      }

      setStories(prev => prev.filter(s => s.id !== storyId));

      // Update active story if deleted
      if (activeStoryId === storyId) {
        const remaining = stories.filter(s => s.id !== storyId);
        setActiveStoryId(remaining.length > 0 ? remaining[0].id : null);
      }
    } catch (err) {
      console.error('Error deleting story:', err);
    }
  };

  // Format question for left nav (show full text, let CSS handle wrapping)
  const formatQuestion = (question) => {
    if (!question) return 'Untitled';
    return question;
  };

  if (loading) {
    return (
      <div className="str-page">
        <div className="str-loading">
          <div className="str-spinner"></div>
          <p>Loading stories...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="str-page">
        <div className="str-error">
          <p>Error: {error}</p>
          <button onClick={fetchStories}>Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="str-page">
      <div className="str-header">
        <h1>Stories</h1>
        <p>Behavioral interview preparation with STAR format</p>
      </div>

      <div className="str-layout">
        {/* Left Panel - Question List */}
        <div className="str-left-panel">
          <div className="str-left-header">
            <span>Questions</span>
            <span className="str-count">{stories.length}</span>
          </div>

          <div className="str-question-list">
            {stories.map(story => (
              <button
                key={story.id}
                className={`str-question-item ${activeStoryId === story.id ? 'active' : ''}`}
                onClick={() => scrollToCard(story.id)}
              >
                <span className="str-question-text">
                  {formatQuestion(story.question)}
                </span>
                {story.type && (
                  <span className="str-question-type">{story.type}</span>
                )}
              </button>
            ))}
          </div>

          <button
            className="str-new-btn"
            onClick={handleCreateStory}
            disabled={isCreating}
          >
            {isCreating ? 'Creating...' : '+ New Story'}
          </button>
        </div>

        {/* Right Panel - Story Cards */}
        <div className="str-right-panel" ref={rightPanelRef}>
          {stories.length === 0 ? (
            <div className="str-empty">
              <div className="str-empty-icon">📝</div>
              <h3>No stories yet</h3>
              <p>Click "+ New Story" to create your first behavioral interview story</p>
            </div>
          ) : (
            stories.map(story => (
              <div
                key={story.id}
                ref={el => (cardRefs.current[story.id] = el)}
              >
                <StoryCard
                  story={story}
                  isActive={activeStoryId === story.id}
                  onUpdate={handleUpdateStory}
                  onDelete={handleDeleteStory}
                />
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

export default StoriesPage;
