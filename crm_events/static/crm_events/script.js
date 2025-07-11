$(document).ready(function() {
    var companyFilter = $('#companyFilter');
    var jobTitleFilter = $('#jobTitleFilter');
    var cityFilter = $('#cityFilter');
    var stateFilter = $('#stateFilter');
    var hostingMin = $('#hostingMin');
    var hostingMax = $('#hostingMax');
    var registeredMin = $('#registeredMin');
    var registeredMax = $('#registeredMax');
    var sortBy = $('#sortBy');
    var applyFiltersBtn = $('#applyFilters');
    var clearFiltersBtn = $('#clearFilters');
    var userListBody = $('#userListBody');
    var loadingMessage = $('#loadingMessage');
    var noUsersMessage = $('#noUsersMessage');
    var prevPageBtn = $('#prevPage');
    var nextPageBtn = $('#nextPage');
    var pageInfo = $('#pageInfo');
    var pageSizeSelect = $('#pageSizeSelect');

    var emailModal = $("#emailModal");
    var openEmailModalBtn = $("#openEmailModalBtn");
    var closeButton = $(".close-button");
    var sendEmailBtnModal = $("#sendEmailBtnModal");
    var emailSubjectModal = $("#emailSubjectModal");
    var emailBodyModal = $("#emailBodyModal");
    var eventSelectModal = $("#eventSelectModal");
    var emailStatusMessageModal = $("#emailStatusMessageModal");

    var currentPage = 1;
    var currentFilters = {};
    var currentSort = sortBy.val();

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    const csrftoken = getCookie('csrftoken');

    function fetchUsers() {
        loadingMessage.show();
        userListBody.empty();
        noUsersMessage.hide();

        var params = {
            page: currentPage,
            page_size: pageSizeSelect.val(),
            ordering: currentSort
        };

        for (const key in currentFilters) {
            if (currentFilters[key] !== null && currentFilters[key] !== '') {
                params[key] = currentFilters[key];
            }
        }

        $.ajax({
            url: '/api/crm/users/',
            method: 'GET',
            dataType: 'json',
            data: params,
            success: function(response) {
                loadingMessage.hide();
                if (response.results.length === 0) {
                    noUsersMessage.show();
                } else {
                    noUsersMessage.hide();
                    response.results.forEach(function(user) {
                        var row = `<tr>
                            <td>${user.username}</td>
                            <td>${user.email || 'N/A'}</td>
                            <td>${user.company || 'N/A'}</td>
                            <td>${user.job_title || 'N/A'}</td>
                            <td>${(user.city || '') + (user.city && user.state ? ', ' : '') + (user.state || 'N/A')}</td>
                            <td>${user.total_hosting_events}</td>
                            <td>${user.total_attended_events}</td>
                            <td>${new Date(user.date_joined).toLocaleDateString()}</td>
                        </tr>`;
                        userListBody.append(row);
                    });
                }

                prevPageBtn.prop('disabled', !response.previous);
                nextPageBtn.prop('disabled', !response.next);
                const totalPages = Math.ceil(response.count / pageSizeSelect.val()) || 1;
                pageInfo.text(`Page ${currentPage} of ${totalPages}`);
            },
            error: function(xhr, status, error) {
                loadingMessage.hide();
                noUsersMessage.text("Error loading users: " + error).show();
                console.error("Error fetching users:", status, error, xhr.responseText);
            }
        });
    }

    function applyFilters() {
        currentFilters = {
            company: companyFilter.val().trim(),
            job_title: jobTitleFilter.val().trim(),
            city: cityFilter.val().trim(),
            state: stateFilter.val().trim(),
            total_hosting_events_min: hostingMin.val() || null,
            total_hosting_events_max: hostingMax.val() || null,
            total_registered_events_min: registeredMin.val() || null,
            total_registered_events_max: registeredMax.val() || null
        };

        currentPage = 1;
        fetchUsers();
    }

    function clearFilters() {
        companyFilter.val('');
        jobTitleFilter.val('');
        cityFilter.val('');
        stateFilter.val('');
        hostingMin.val('');
        hostingMax.val('');
        registeredMin.val('');
        registeredMax.val('');
        sortBy.val('username');
        currentFilters = {};
        currentSort = 'username';
        currentPage = 1;
        fetchUsers();
    }

    applyFiltersBtn.on('click', applyFilters);
    clearFiltersBtn.on('click', clearFilters);
    sortBy.on('change', function() {
        currentSort = $(this).val();
        currentPage = 1;
        fetchUsers();
    });
    pageSizeSelect.on('change', function() {
        currentPage = 1;
        fetchUsers();
    });
    prevPageBtn.on('click', function() {
        if (currentPage > 1) {
            currentPage--;
            fetchUsers();
        }
    });
    nextPageBtn.on('click', function() {
        currentPage++;
        fetchUsers();
    });

    function loadEventsIntoDropdown() {
        $.ajax({
            url: '/crm/events/',
            method: 'GET',
            success: function(data) {
                eventSelectModal.empty();
                eventSelectModal.append('<option value="">-- Select an Event (Optional) --</option>');
                data.forEach(event => {
                    eventSelectModal.append(`<option value="${event.slug}">${event.title}</option>`);
                });
            },
            error: function(xhr, status, error) {
                console.error("Error loading events for dropdown:", error, xhr.responseText);
                eventSelectModal.empty().append('<option value="">Error loading events</option>');
            }
        });
    }

    openEmailModalBtn.on("click", function() {
        emailModal.css("display", "block");
        emailStatusMessageModal.text('').removeClass('success error');
        loadEventsIntoDropdown();
    });

    closeButton.on("click", function() {
        emailModal.css("display", "none");
        emailStatusMessageModal.text('');
    });

    $(window).on("click", function(event) {
        if (event.target == emailModal[0]) {
            emailModal.css("display", "none");
            emailStatusMessageModal.text('');
        }
    });

    sendEmailBtnModal.on("click", function() {
        var subject = emailSubjectModal.val().trim();
        var body = emailBodyModal.val().trim();
        var eventSlug = eventSelectModal.val();

        if (!subject) {
            emailStatusMessageModal.text("Subject is required.").addClass('error').removeClass('success');
            return;
        }
        if (!body) {
            emailStatusMessageModal.text("Email body must be provided.").addClass('error').removeClass('success');
            return;
        }

        var payloadData = {
            subject: subject,
            body: body,
        };

        if (eventSlug) {
            payloadData.event_slug = eventSlug;
        }

        for (const key in currentFilters) {
            if (currentFilters[key] !== null && currentFilters[key] !== '') {
                payloadData[key] = currentFilters[key];
            }
        }

        $.ajax({
            url: '/api/crm/send-emails/',
            method: 'POST',
            dataType: 'json',
            contentType: 'application/json',
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: JSON.stringify(payloadData),
            beforeSend: function() {
                sendEmailBtnModal.prop('disabled', true).text('Sending...');
                emailStatusMessageModal.text('Sending emails, please wait...').removeClass('error success');
            },
            success: function(data) {
                emailStatusMessageModal.text(data.message).removeClass('error').addClass('success');
                emailSubjectModal.val('');
                emailBodyModal.val('');
                eventSelectModal.val('');
                sendEmailBtnModal.prop('disabled', false).text('Send Email');
            },
            error: function(xhr) {
                var errorMessage = "An unexpected error occurred.";
                try {
                    var errorData = xhr.responseJSON;
                    if (errorData) {
                        if (errorData.message) {
                            errorMessage = errorData.message;
                        } else if (errorData.detail) {
                            errorMessage = errorData.detail;
                        } else if (errorData.non_field_errors) {
                            errorMessage = errorData.non_field_errors.join(', ');
                        } else {
                            let fieldErrors = [];
                            for (const key in errorData) {
                                if (Array.isArray(errorData[key])) {
                                    fieldErrors.push(`${key}: ${errorData[key].join(', ')}`);
                                } else {
                                    fieldErrors.push(`${key}: ${errorData[key]}`);
                                }
                            }
                            if (fieldErrors.length > 0) {
                                errorMessage = fieldErrors.join('; ');
                            }
                        }
                    }
                } catch (e) {
                    console.error("Failed to parse error response:", e);
                }
                emailStatusMessageModal.text("Error: " + errorMessage).removeClass('success').addClass('error');
                sendEmailBtnModal.prop('disabled', false).text('Send Email');
                console.error("AJAX Error:", xhr.status, xhr.statusText, xhr.responseText);
            }
        });
    });

    fetchUsers();
});
