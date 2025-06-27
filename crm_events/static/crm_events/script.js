$(document).ready(function() {
    // --- Khai báo biến DOM elements (chung cho cả trang và modal) ---
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

    // --- Biến cho Pagination và Filter State ---
    var currentPage = 1;
    var currentFilters = {};
    var currentSort = sortBy.val();
    var currentSearch = ''; // Thêm biến search nếu có

    // --- Modal Elements ---
    var emailModal = $("#emailModal");
    var openEmailModalBtn = $("#openEmailModalBtn");
    var closeButton = $(".close-button");
    var sendEmailBtnModal = $("#sendEmailBtnModal");
    var emailSubjectModal = $("#emailSubjectModal");
    var emailBodyModal = $("#emailBodyModal");
    var emailHtmlBodyModal = $("#emailHtmlBodyModal");
    var emailStatusMessageModal = $("#emailStatusMessageModal");


    // --- Hàm Fetch Users ---
    function fetchUsers() {
        loadingMessage.show();
        userListBody.empty(); // Clear previous users
        noUsersMessage.hide();

        var params = {
            page: currentPage,
            page_size: pageSizeSelect.val(),
            ordering: currentSort
        };

        // Thêm các filter vào params
        if (currentFilters.company) params.company = currentFilters.company;
        if (currentFilters.job_title) params.job_title = currentFilters.job_title;
        if (currentFilters.city) params.city = currentFilters.city;
        if (currentFilters.state) params.state = currentFilters.state;
        if (currentFilters.total_hosting_events_min) params.total_hosting_events_min = currentFilters.total_hosting_events_min;
        if (currentFilters.total_hosting_events_max) params.total_hosting_events_max = currentFilters.total_hosting_events_max;
        if (currentFilters.total_registered_events_min) params.total_registered_events_min = currentFilters.total_registered_events_min;
        if (currentFilters.total_registered_events_max) params.total_registered_events_max = currentFilters.total_registered_events_max;
        // Thêm currentSearch nếu bạn có một trường tìm kiếm chung
        if (currentSearch) params.search = currentSearch;


        $.ajax({
            url: '/api/crm/users/', // Đảm bảo URL này đúng với API endpoint của bạn
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

                // Cập nhật Pagination
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

    // --- Hàm Apply Filters ---
    function applyFilters() {
        currentFilters = {
            // Sử dụng .trim() cho các trường kiểu văn bản
            company: companyFilter.val().trim(),
            job_title: jobTitleFilter.val().trim(),
            city: cityFilter.val().trim(),
            state: stateFilter.val().trim(),

            // Các trường số không cần trim
            total_hosting_events_min: hostingMin.val() || null,
            total_hosting_events_max: hostingMax.val() || null,
            total_registered_events_min: registeredMin.val() || null,
            total_registered_events_max: registeredMax.val() || null
        };

        // Loại bỏ các bộ lọc rỗng sau khi trim (nếu một trường chỉ chứa khoảng trắng)
        for (var key in currentFilters) {
            if (currentFilters.hasOwnProperty(key)) {
                // Kiểm tra nếu giá trị là chuỗi và rỗng (sau khi trim) thì xóa bỏ
                // hoặc nếu giá trị là null (từ các trường số)
                if ((typeof currentFilters[key] === 'string' && currentFilters[key] === '') || currentFilters[key] === null) {
                    delete currentFilters[key];
                }
            }
        }

        currentPage = 1; // Reset to first page on new filter
        fetchUsers();
    }

    // --- Hàm Clear Filters ---
    function clearFilters() {
        companyFilter.val('');
        jobTitleFilter.val('');
        cityFilter.val('');
        stateFilter.val('');
        hostingMin.val('');
        hostingMax.val('');
        registeredMin.val('');
        registeredMax.val('');
        sortBy.val('username'); // Reset sort to default
        currentFilters = {}; // Đảm bảo clear hết filter
        currentSort = 'username';
        currentPage = 1;
        fetchUsers();
    }

    // --- Event Listeners cho bộ lọc và phân trang ---
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

    // --- Logic cho Modal Email (NEW) ---

    // Mở modal khi click nút
    openEmailModalBtn.on("click", function() {
        emailModal.css("display", "block");
        emailStatusMessageModal.text(''); // Xóa trạng thái tin nhắn cũ
        emailStatusMessageModal.removeClass('success error');
    });

    // Đóng modal khi click nút đóng (x)
    closeButton.on("click", function() {
        emailModal.css("display", "none");
    });

    // Đóng modal khi click ra bên ngoài modal content
    $(window).on("click", function(event) {
        if (event.target == emailModal[0]) { // Sử dụng [0] để lấy phần tử DOM gốc từ đối tượng jQuery
            emailModal.css("display", "none");
        }
    });

    // Xử lý gửi email từ modal
    sendEmailBtnModal.on("click", function() {
        var subject = emailSubjectModal.val();
        var body = emailBodyModal.val();
        var htmlBody = emailHtmlBodyModal.val();
        var csrfToken = $('input[name="csrfmiddlewaretoken"]').val(); // Lấy CSRF token

        if (!subject || (!body && !htmlBody)) {
            emailStatusMessageModal.text("Subject and at least one body field are required.").addClass('error').removeClass('success');
            return;
        }

        // Tạo đối tượng chứa các tham số lọc hiện tại
        var filterParams = $.extend({}, currentFilters); // Sao chép currentFilters
        filterParams.ordering = currentSort; // Thêm ordering
        filterParams.search = currentSearch; // Thêm search nếu có

        $.ajax({
            url: '/api/crm/send-emails/', // API endpoint để gửi email
            method: 'POST',
            dataType: 'json',
            contentType: 'application/json', // Đảm bảo server biết đây là JSON
            headers: {
                'X-CSRFToken': csrfToken // Gửi CSRF token trong header
            },
            data: JSON.stringify({ // Chuyển dữ liệu sang JSON string
                subject: subject,
                body: body,
                html_body: htmlBody,
                filters: filterParams // Gửi các filter hiện tại
            }),
            beforeSend: function() {
                sendEmailBtnModal.prop('disabled', true).text('Sending...');
                emailStatusMessageModal.text('Sending emails, please wait...').removeClass('error success');
            },
            success: function(data) {
                emailStatusMessageModal.text(data.message);
                if (data.status === 'success') {
                    emailStatusMessageModal.removeClass('error').addClass('success');
                    // Xóa nội dung form sau khi gửi thành công
                    emailSubjectModal.val('');
                    emailBodyModal.val('');
                    emailHtmlBodyModal.val('');
                    // Tùy chọn: Đóng modal sau khi gửi
                    // emailModal.css("display", "none");
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

    // --- Initial Load ---
    fetchUsers();
});