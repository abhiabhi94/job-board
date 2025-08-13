// This file is auto-generated from main.js for testing purposes
// DO NOT EDIT MANUALLY - Run 'npm run generate:test-module' to update

// Export the main.js functionality as a module for testing
export function initializeMainJs() {
    
        // Dark mode toggle functionality
        const themeToggle = document.getElementById('theme-toggle');
    
        themeToggle.addEventListener('click', function() {
            const isDark = document.documentElement.classList.contains('dark');
    
            if (isDark) {
                document.documentElement.classList.remove('dark');
                localStorage.setItem('theme', 'light');
            } else {
                document.documentElement.classList.add('dark');
                localStorage.setItem('theme', 'dark');
            }
        });
    
        // Add staggered animation to job cards
        const jobCards = document.querySelectorAll('article');
        jobCards.forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            setTimeout(() => {
                card.style.transition = 'opacity 0.6s ease-out, transform 0.6s ease-out';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 100);
        });
    
        // Add keyboard navigation for tag labels
        const tagLabels = document.querySelectorAll('.tag-label');
        tagLabels.forEach(label => {
            label.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    const checkbox = document.getElementById(label.getAttribute('for'));
                    if (checkbox) {
                        checkbox.checked = !checkbox.checked;
                        checkbox.dispatchEvent(new Event('change'));
                    }
                }
            });
        });
    
        // Add focus management for job cards
        const focusableJobCards = document.querySelectorAll('article[role="button"]');
        focusableJobCards.forEach(card => {
            card.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    card.click();
                }
            });
        });
    
        // Cache common elements
        const filterForm = document.getElementById('filter-form');
        //  Enable form submission when tags are clicked
        const tagInputs = document.querySelectorAll('.tag-checkbox');
        tagInputs.forEach(input => {
            input.addEventListener('change', function () {
                // Add loading state to the changed tag
                const label = input.nextElementSibling;
                if (label) {
                    label.style.opacity = '0.6';
                    label.style.transform = 'scale(0.95)';
                }
    
                // Show loading on submit button
                const submitBtn = document.getElementById('filter-submit-btn');
                if (submitBtn) {
                    submitBtn.classList.add('loading');
                }
    
                filterForm?.submit();
            });
        });
    
        // Location dropdown functionality
        const locationButton = document.getElementById('location-button');
        const locationOptions = document.getElementById('location-options');
        const locationHiddenInput = locationOptions?.querySelector('input[name="location"]');
        const locationText = locationButton?.querySelector('.location-text');
        const locationArrow = locationButton?.querySelector('.location-arrow');
        const locationSearch = document.getElementById('location-search');
    
        // Sort dropdown functionality
        const sortButton = document.getElementById('sort-button');
        const sortOptions = document.getElementById('sort-options');
        const hiddenInput = sortOptions?.querySelector('input[name="sort"]');
        const sortText = sortButton?.querySelector('.sort-text');
        const sortArrow = sortButton?.querySelector('.sort-arrow');
    
        // Location dropdown functions
        if (locationButton && locationOptions) {
            function closeLocationDropdown() {
                locationOptions.classList.add('hidden');
                if (locationArrow) {
                    locationArrow.style.transform = 'rotate(0deg)';
                }
            }
    
            function openLocationDropdown() {
                locationOptions.classList.remove('hidden');
                if (locationArrow) {
                    locationArrow.style.transform = 'rotate(180deg)';
                }
                // Focus search input when dropdown opens
                setTimeout(() => {
                    if (locationSearch) locationSearch.focus();
                }, 100);
            }
    
            // Toggle location dropdown
            locationButton.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
    
                if (locationOptions.classList.contains('hidden')) {
                    openLocationDropdown();
                } else {
                    closeLocationDropdown();
                }
            });
    
            // Handle location option selection
            locationOptions.addEventListener('click', function (e) {
                const option = e.target.closest('.location-option');
                if (!option) return;
    
                const value = option.dataset.value;
                const text = option.textContent.trim();
    
                // Update hidden input
                if (locationHiddenInput) {
                    locationHiddenInput.value = value;
                }
    
                // Update button text
                if (locationText) {
                    locationText.textContent = text;
                }
    
                // Close dropdown
                closeLocationDropdown();
    
                // Submit form
                document.getElementById('filter-form')?.submit();
            });
    
            // Search functionality
            if (locationSearch) {
                locationSearch.addEventListener('input', function (e) {
                    const searchTerm = e.target.value.toLowerCase();
                    const options = locationOptions.querySelectorAll('.location-option');
    
                    options.forEach(option => {
                        const searchText = option.dataset.search || option.textContent.toLowerCase();
                        if (searchText.includes(searchTerm)) {
                            option.style.display = 'block';
                        } else {
                            option.style.display = 'none';
                        }
                    });
                });
    
                // Prevent form submission when Enter is pressed in search
                locationSearch.addEventListener('keydown', function (e) {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        // Select first visible option
                        const visibleOption = locationOptions.querySelector('.location-option[style="display: block"], .location-option:not([style*="display: none"])');
                        if (visibleOption && visibleOption !== locationOptions.querySelector('.location-option')) {
                            visibleOption.click();
                        }
                    }
                });
            }
    
            // Close location dropdown when clicking outside
            document.addEventListener('click', function (e) {
                if (!locationButton.closest('.location-dropdown').contains(e.target)) {
                    closeLocationDropdown();
                }
            });
    
            // Close location dropdown on escape key
            document.addEventListener('keydown', function (e) {
                if (e.key === 'Escape') {
                    closeLocationDropdown();
                }
            });
        }
    
        if (sortButton && sortOptions) {
    
        function closeDropdown() {
            sortOptions.classList.add('hidden');
            if (sortArrow) {
                sortArrow.style.transform = 'rotate(0deg)';
            }
        }
    
        function openDropdown() {
            sortOptions.classList.remove('hidden');
            if (sortArrow) {
                sortArrow.style.transform = 'rotate(180deg)';
            }
        }
    
        // Toggle dropdown
        sortButton.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
    
            if (sortOptions.classList.contains('hidden')) {
                openDropdown();
            } else {
                closeDropdown();
            }
        });
    
        // Handle option selection
        sortOptions.addEventListener('click', function (e) {
            const option = e.target.closest('.sort-option');
            if (!option) return;
    
            const value = option.dataset.value;
            const text = option.textContent.trim();
    
            // Update hidden input
            if (hiddenInput) {
                hiddenInput.value = value;
            }
    
            // Update button text
            if (sortText) {
                sortText.textContent = text;
            }
    
            // Close dropdown
            closeDropdown();
    
            // Submit form
            document.getElementById('filter-form')?.submit();
        });
    
        // Close dropdown when clicking outside
        document.addEventListener('click', function (e) {
            if (!sortButton.closest('.sort-dropdown').contains(e.target)) {
                closeDropdown();
            }
        });
    
        // Close dropdown on escape key
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                closeDropdown();
            }
        });
        }
    
        // Load More Jobs functionality
        let currentPage = parseInt(document.querySelector('[data-current-page]')?.getAttribute('data-current-page') || '1');
        let isLoading = false;
        let infiniteScrollEnabled = false;
    
        function loadJobs(nextPage) {
            if (isLoading) return;
    
            isLoading = true;
            const loadMoreBtn = document.getElementById('load-more-btn');
            if (loadMoreBtn) {
                loadMoreBtn.classList.add('loading');
            }
    
            // Get current form data to maintain filters
            const formData = new FormData(document.getElementById('filter-form'));
            formData.set('page', nextPage);
    
            // Convert FormData to URLSearchParams
            const params = new URLSearchParams();
            for (let [key, value] of formData.entries()) {
                params.append(key, value);
            }
    
            // Get the base URL from the form action or current page
            const baseUrl = document.getElementById('filter-form').action || window.location.pathname;
    
            fetch(`${baseUrl}?${params.toString()}`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.text())
            .then(html => {
                // Parse the response to extract job cards
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const newJobCards = doc.querySelectorAll('article[data-job-id]');
    
                // Get the job grid container
                const jobGrid = document.querySelector('.grid.grid-cols-1.md\\:grid-cols-2.lg\\:grid-cols-3');
    
                // Add new job cards with animation
                newJobCards.forEach((card, index) => {
                    card.style.opacity = '0';
                    card.style.transform = 'translateY(20px)';
                    jobGrid.appendChild(card);
    
                    setTimeout(() => {
                        card.style.transition = 'opacity 0.6s ease-out, transform 0.6s ease-out';
                        card.style.opacity = '1';
                        card.style.transform = 'translateY(0)';
                    }, index * 100);
                });
    
                // Initialize seen jobs functionality for newly loaded cards
                setTimeout(() => {
                    const seenJobs = getSeenJobs();
                    newJobCards.forEach(jobCard => {
                        const jobId = jobCard.dataset.jobId;
    
                        // Apply seen state if job is marked as seen
                        if (jobId && seenJobs.includes(jobId)) {
                            updateJobVisualState(jobCard, true);
                        }
    
                        // Add event listener if not already added
                        const btn = jobCard.querySelector('.seen-job-btn');
                        if (btn && !btn.hasAttribute('data-listener-added')) {
                            btn.addEventListener('click', handleSeenJobClick);
                            btn.setAttribute('data-listener-added', 'true');
                        }
                    });
                }, 1000);
    
                currentPage = parseInt(nextPage);
    
                // Check if there are more pages
                const newPagination = doc.querySelector('[data-has-next]');
                if (!newPagination || newPagination.getAttribute('data-has-next') === 'false') {
                    if (loadMoreBtn) {
                        loadMoreBtn.style.display = 'none';
                    }
    
                    // Show "All jobs loaded" message
                    const allLoadedMsg = document.createElement('div');
                    allLoadedMsg.className = 'text-sm text-gray-500 dark:text-gray-400 py-4';
                    allLoadedMsg.textContent = 'All jobs loaded!';
                    if (loadMoreBtn && loadMoreBtn.parentNode) {
                        loadMoreBtn.parentNode.replaceChild(allLoadedMsg, loadMoreBtn);
                    }
                } else {
                    if (loadMoreBtn) {
                        const nextPageNum = parseInt(nextPage) + 1;
                        loadMoreBtn.setAttribute('data-next-page', nextPageNum);
                        loadMoreBtn.setAttribute('onclick', `loadMoreJobs(${nextPageNum})`);
                    }
                }
            })
            .catch(error => {
                console.error('Error loading more jobs:', error);
                // Show error message
                const errorMsg = document.createElement('div');
                errorMsg.className = 'text-sm text-red-500 py-2';
                errorMsg.textContent = 'Failed to load more jobs. Please try again.';
                if (loadMoreBtn && loadMoreBtn.parentNode) {
                    loadMoreBtn.parentNode.insertBefore(errorMsg, loadMoreBtn);
                }
            })
            .finally(() => {
                isLoading = false;
                if (loadMoreBtn) {
                    loadMoreBtn.classList.remove('loading');
                }
            });
        }
    
    
        function enableInfiniteScroll() {
            let scrollTimeout;
    
            window.addEventListener('scroll', function() {
                // Debounce scroll events
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(() => {
                    // Check if user is near bottom of page
                    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                    const windowHeight = window.innerHeight;
                    const documentHeight = document.documentElement.scrollHeight;
    
                    // Load more when user is 300px from bottom
                    if (scrollTop + windowHeight >= documentHeight - 300) {
                        const loadMoreBtn = document.getElementById('load-more-btn');
                        if (loadMoreBtn && loadMoreBtn.style.display !== 'none') {
                            // Calculate next page based on current page
                            const nextPage = parseInt(currentPage) + 1;
                            loadJobs(nextPage);
                        }
                    }
                }, 100);
            });
        }
    
        // Function to clear all filters
        window.clearAllFilters = function() {
            const form = document.getElementById('filter-form');
            if (form) {
                // Clear all form inputs
                form.reset();
    
                // Uncheck all tag checkboxes
                const tagInputs = form.querySelectorAll('.tag-checkbox');
                tagInputs.forEach(input => input.checked = false);
    
                // Update tag labels visual state
                const tagLabels = form.querySelectorAll('.tag-label');
                tagLabels.forEach(label => {
                    label.classList.remove('bg-primary', 'text-white');
                    label.classList.add('bg-gray-100', 'text-gray-700');
                });
    
                // Reset location dropdown
                const locationText = document.querySelector('.location-text');
                if (locationText) {
                    locationText.textContent = 'Any Location';
                }
    
                // Submit the form to reload with no filters
                form.submit();
            }
        };
    
        // Seen Jobs Management
        const SEEN_JOBS_KEY = 'job-board-seen-jobs';
    
        function getSeenJobs() {
            try {
                const seenJobs = localStorage.getItem(SEEN_JOBS_KEY);
                return seenJobs ? JSON.parse(seenJobs) : [];
            } catch (error) {
                console.error('Error reading seen jobs from localStorage:', error);
                return [];
            }
        }
    
        function markJobAsSeen(jobId, seen = true) {
            try {
                let seenJobs = getSeenJobs();
                const index = seenJobs.indexOf(jobId);
    
                if (seen && index === -1) {
                    seenJobs.push(jobId);
                } else if (!seen && index !== -1) {
                    seenJobs.splice(index, 1);
                }
    
                localStorage.setItem(SEEN_JOBS_KEY, JSON.stringify(seenJobs));
                return true;
            } catch (error) {
                console.error('Error updating seen jobs in localStorage:', error);
                return false;
            }
        }
    
        function isJobSeen(jobId) {
            const seenJobs = getSeenJobs();
            return seenJobs.includes(jobId);
        }
    
        function clearSeenJobs() {
            try {
                localStorage.removeItem(SEEN_JOBS_KEY);
                return true;
            } catch (error) {
                console.error('Error clearing seen jobs from localStorage:', error);
                return false;
            }
        }
    
        // Apply visual feedback for seen jobs
        function updateJobVisualState(jobCard, isSeen) {
            if (!jobCard) {
                console.error('updateJobVisualState: jobCard is null');
                return;
            }
    
            if (isSeen) {
                jobCard.classList.add('job-seen');
    
                // Apply seen styles and disable hover effects
                jobCard.style.opacity = '0.2';
                jobCard.style.filter = 'brightness(0.8)';
                jobCard.style.pointerEvents = 'auto'; // Keep clickable
    
                // Disable hover effects by removing/overriding hover handlers
                jobCard.onmouseenter = null;
                jobCard.onmouseleave = null;
                // Use CSS class for transform to avoid overriding existing transforms
                jobCard.classList.add('job-seen-transform');
    
                // Update button state
                const btn = jobCard.querySelector('.seen-job-btn');
                if (btn) {
                    btn.style.opacity = '0.6';
                    const seenIcon = btn.querySelector('.seen-icon');
                    const unseenIcon = btn.querySelector('.unseen-icon');
    
                    if (seenIcon) seenIcon.classList.remove('hidden');
                    if (unseenIcon) unseenIcon.classList.add('hidden');
                    btn.title = 'Mark as unseen';
                    btn.setAttribute('aria-label', 'Mark job as unseen');
                }
            } else {
                jobCard.classList.remove('job-seen');
    
                // Restore normal styles
                jobCard.style.opacity = '';
                jobCard.style.filter = '';
                // Remove transform class instead of resetting inline style
                jobCard.classList.remove('job-seen-transform');
    
                // Restore hover effects
                jobCard.onmouseenter = function() { this.style.transform = 'translateY(-8px) scale(1.02)'; };
                jobCard.onmouseleave = function() { this.style.transform = 'translateY(0) scale(1)'; };
    
                // Update button state
                const btn = jobCard.querySelector('.seen-job-btn');
                if (btn) {
                    btn.style.opacity = '';
                    const seenIcon = btn.querySelector('.seen-icon');
                    const unseenIcon = btn.querySelector('.unseen-icon');
    
                    if (seenIcon) seenIcon.classList.add('hidden');
                    if (unseenIcon) unseenIcon.classList.remove('hidden');
                    btn.title = 'Mark as seen';
                    btn.setAttribute('aria-label', 'Mark job as seen');
                }
            }
        }
    
        // Handle seen job button clicks
        function handleSeenJobClick(event) {
            event.preventDefault();
            event.stopPropagation();
    
            const btn = event.currentTarget;
            const jobId = btn.dataset.jobId;
            const jobCard = btn.closest('article');
    
            if (!jobId || !jobCard) return;
    
            const currentlySeen = isJobSeen(jobId);
            const newSeenState = !currentlySeen;
    
            if (markJobAsSeen(jobId, newSeenState)) {
                updateJobVisualState(jobCard, newSeenState);
            }
        }
    
        // Restore seen states on page load
        function restoreSeenStates() {
            const jobCards = document.querySelectorAll('article[data-job-id]');
            const seenJobs = getSeenJobs();
    
            jobCards.forEach(jobCard => {
                const jobId = jobCard.dataset.jobId;
                if (jobId && seenJobs.includes(jobId)) {
                    updateJobVisualState(jobCard, true);
                }
            });
        }
    
        // Initialize seen job functionality
        function initializeSeenJobs() {
            // Restore seen states for existing jobs
            restoreSeenStates();
    
            // Add event listeners to seen job buttons
            const seenJobBtns = document.querySelectorAll('.seen-job-btn');
            seenJobBtns.forEach(btn => {
                if (!btn.hasAttribute('data-listener-added')) {
                    btn.addEventListener('click', handleSeenJobClick);
                    btn.setAttribute('data-listener-added', 'true');
                }
            });
        }
    
        // Initialize with retry mechanism
        function initializeSeenJobsWithRetry(retryCount = 0) {
            const maxRetries = 3;
            const jobCards = document.querySelectorAll('article[data-job-id]');
            const seenJobs = getSeenJobs();
    
            if (jobCards.length === 0 && retryCount < maxRetries) {
                setTimeout(() => initializeSeenJobsWithRetry(retryCount + 1), 500);
                return;
            }
    
            initializeSeenJobs();
    
            // Double-check that all seen jobs are visually marked after a brief delay
            setTimeout(() => {
                jobCards.forEach(jobCard => {
                    const jobId = jobCard.dataset.jobId;
                    if (jobId && seenJobs.includes(jobId) && !jobCard.classList.contains('job-seen')) {
                        updateJobVisualState(jobCard, true);
                    }
                });
            }, 200);
        }
    
        // Initialize seen jobs on page load with retry mechanism
        setTimeout(() => {
            initializeSeenJobsWithRetry();
        }, 1000);
    
        // Also initialize on window load as backup
        window.addEventListener('load', () => {
            setTimeout(() => {
                initializeSeenJobsWithRetry();
            }, 500);
        });
    
        // Extend loadMoreJobs to include seen job initialization for new jobs
        window.loadMoreJobs = function(nextPage) {
            // Enable infinite scroll after first manual load
            if (!infiniteScrollEnabled) {
                infiniteScrollEnabled = true;
                enableInfiniteScroll();
            }
            loadJobs(parseInt(nextPage));
    
            // Wait for new content to be added, then initialize seen jobs for new cards
            setTimeout(() => {
                const seenJobs = getSeenJobs();
                document.querySelectorAll('article[data-job-id]').forEach(jobCard => {
                    const jobId = jobCard.dataset.jobId;
    
                    // Apply seen state if job is marked as seen
                    if (jobId && seenJobs.includes(jobId)) {
                        updateJobVisualState(jobCard, true);
                    }
    
                    // Add event listener if not already added
                    const btn = jobCard.querySelector('.seen-job-btn');
                    if (btn && !btn.hasAttribute('data-listener-added')) {
                        btn.addEventListener('click', handleSeenJobClick);
                        btn.setAttribute('data-listener-added', 'true');
                    }
                });
            }, 1000);
        };
    
        // Make functions available globally for testing
        window.seenJobsAPI = {
            getSeenJobs,
            markJobAsSeen,
            isJobSeen,
            clearSeenJobs,
            updateJobVisualState,
            handleSeenJobClick,
            restoreSeenStates,
            initializeSeenJobs
        };
    
        // Also expose loadJobs for testing
        window.loadJobs = loadJobs;
    
}
