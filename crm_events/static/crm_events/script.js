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

    var currentPage = 1;
    var currentFilters = {};
    var currentSort = sortBy.val();
    var currentSearch = '';

    var emailModal = $("#emailModal");
    var openEmailModalBtn = $("#openEmailModalBtn");
    var closeButton = $(".close-button");
    var sendEmailBtnModal = $("#sendEmailBtnModal");
    var emailSubjectModal = $("#emailSubjectModal");
    var emailBodyModal = $("#emailBodyModal");
    var emailStatusMessageModal = $("#emailStatusMessageModal");

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

    function fetchUsers() {
        loadingMessage.show();
        userListBody.empty();
        noUsersMessage.hide();

        var params = {
            page: currentPage,
            page_size: pageSizeSelect.val(),
            ordering: currentSort
        };

        if (currentFilters.company) params.company = currentFilters.company;
        if (currentFilters.job_title) params.job_title = currentFilters.job_title;
        if (currentFilters.city) params.city = currentFilters.city;
        if (currentFilters.state) params.state = currentFilters.state;
        if (currentFilters.total_hosting_events_min) params.total_hosting_events_min = currentFilters.total_hosting_events_min;
        if (currentFilters.total_hosting_events_max) params.total_hosting_events_max = currentFilters.total_hosting_events_max;
        if (currentFilters.total_registered_events_min) params.total_registered_events_min = currentFilters.total_registered_events_min;
        if (currentFilters.total_registered_events_max) params.total_registered_events_max = currentFilters.total_registered_events_max;
        if (currentSearch) params.search = currentSearch;

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
                    response.results.forEach(function(user) {
                        var row = `<tr>
                            <td>${user.username}</td>
                            <td>${user.email}</td>
                            <td>${user.company || 'N/A'}</td>
                            <td>${user.job_title || 'N/A'}</td>
                            <td>${user.city || 'N/A'}, ${user.state || 'N/A'}</td>
                            <td>${user.total_hosting_events}</td>
                            <td>${user.total_registered_events}</td>
                            <td>${new Date(user.date_joined).toLocaleDateString()}</td>
                        </tr>`;
                        userListBody.append(row);
                    });
                }

                prevPageBtn.prop('disabled', !response.previous);
                nextPageBtn.prop('disabled', !response.next);
                pageInfo.text(`Page ${currentPage} of ${Math.ceil(response.count / pageSizeSelect.val())}`);
            },
            error: function(xhr, status, error) {
                loadingMessage.hide();
                noUsersMessage.text("Error loading users: " + error).show();
                console.error("Error fetching users:", status, error);
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

        for (var key in currentFilters) {
            if (currentFilters.hasOwnProperty(key)) {
                if ((typeof currentFilters[key] === 'string' && currentFilters[key] === '') || currentFilters[key] === null) {
                    delete currentFilters[key];
                }
            }
        }

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

    openEmailModalBtn.on("click", function() {
        emailModal.css("display", "block");
        emailStatusMessageModal.text('');
        emailStatusMessageModal.removeClass('success error');
    });

    closeButton.on("click", function() {
        emailModal.css("display", "none");
    });

    $(window).on("click", function(event) {
        if (event.target == emailModal[0]) {
            emailModal.css("display", "none");
        }
    });

    sendEmailBtnModal.on("click", function() {
        var subject = emailSubjectModal.val().trim();
        var body = emailBodyModal.val().trim();

        var csrfToken = getCookie('csrftoken');

        if (!subject) {
            emailStatusMessageModal.text("Subject is required.").addClass('error').removeClass('success');
            return;
        }
        if (!body) {
            emailStatusMessageModal.text("Email body must be provided.").addClass('error').removeClass('success');
            return;
        }

        var payloadData = $.extend({}, currentFilters);

        if (currentSort) {
            payloadData.ordering = currentSort;
        }
        if (currentSearch) {
            payloadData.search = currentSearch;
        }

        payloadData.subject = subject;
        payloadData.body = body;

        $.ajax({
            url: '/api/crm/send-emails/',
            method: 'POST',
            dataType: 'json',
            contentType: 'application/json',
            headers: {
                'X-CSRFToken': csrfToken
            },
            data: JSON.stringify(payloadData),
            beforeSend: function() {
                sendEmailBtnModal.prop('disabled', true).text('Sending...');
                emailStatusMessageModal.text('Sending emails, please wait...').removeClass('error success');
            },
            success: function(data) {
                emailStatusMessageModal.text(data.message);
                if (data.status === 'success') {
                    emailStatusMessageModal.removeClass('error').addClass('success');
                    emailSubjectModal.val('');
                    emailBodyModal.val('');
                } else {
                    emailStatusMessageModal.removeClass('success').addClass('error');
                }
                sendEmailBtnModal.prop('disabled', false).text('Send Email');
            },
            error: function(xhr, textStatus, errorThrown) {
                var errorMessage = "An unexpected error occurred.";
                try {
                    var errorData = JSON.parse(xhr.responseText);
                    if (errorData.detail) {
                        errorMessage = errorData.detail;
                    } else if (errorData.message) {
                        errorMessage = errorData.message;
                    } else if (errorData.error) {
                        errorMessage = errorData.error;
                    }
                } catch (e) {
                    console.error("Failed to parse error response:", e);
                }
                emailStatusMessageModal.text("Error: " + errorMessage).removeClass('success').addClass('error');
                sendEmailBtnModal.prop('disabled', false).text('Send Email');
                console.error("AJAX Error:", textStatus, errorThrown, xhr.responseText);
            }
        });
    });

    fetchUsers();
});