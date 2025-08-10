document.addEventListener('DOMContentLoaded', function () {
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

    if (!sortButton || !sortOptions) return;

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

    window.loadMoreJobs = function(nextPage) {
        // Enable infinite scroll after first manual load
        if (!infiniteScrollEnabled) {
            infiniteScrollEnabled = true;
            enableInfiniteScroll();
        }
        loadJobs(parseInt(nextPage));
    };

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
});
