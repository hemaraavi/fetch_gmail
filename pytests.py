import pytest
import json
from unittest.mock import ANY,Mock  # Import ANY for matching any value in assertions
from script import *


class MockResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self.json_data = json_data

    def json(self):
        return self.json_data


def test_load_rules(mocker):
    # Given
    expected_rules = [{
        "conditions": [{"field": "From", "predicate": "contains", "value": "example.com"}],
        "actions": [{"action": "Mark as Read"}]
    }]
    mocker.patch("builtins.open", mocker.mock_open(read_data=json.dumps({"rules": expected_rules})))
    # When
    rules = load_rules()
    # Then
    assert rules == expected_rules, "Failed to load rules correctly"

def test_gmail_authenticate_valid_credentials(mocker):
    # Mock the InstalledAppFlow and the pickle.load to return valid credentials
    creds_mock = mocker.Mock()
    creds_mock.valid = True
    mocker.patch("pickle.load", return_value=creds_mock)
    mocker.patch("google_auth_oauthlib.flow.InstalledAppFlow.run_local_server", return_value=creds_mock)
    mocker.patch("googleapiclient.discovery.build", return_value="Gmail service")
    # Expected outcome
    service = gmail_authenticate()
    assert service , "Service did not authenticate as expected with valid credentials"

def test_build_conditions_contains():
    # Given
    where_conditions = []
    params = {}
    condition = {"field": "From", "predicate": "contains", "value": "test@example.com"}
    # When
    updated_where_conditions, updated_params = build_conditions(where_conditions, params, condition)
    # Then
    assert len(updated_where_conditions) == 1
    assert "sender LIKE :sender_like" in updated_where_conditions
    assert updated_params == {"sender_like": "%test@example.com%"}, "Parameters did not match expected value"



def test_modify_api_call(mocker):
    # Mock requests.post to return a mock response
    mocked_post = mocker.patch("requests.post")

    # Call the function with example data
    as_read_ids = ["id1", "id2"]
    unread_ids = ["id3", "id4"]
    move_ids = ["id5", "id6"]

    modify_api_call(as_read_ids, unread_ids, move_ids)

    # Assert requests.post was called with the correct arguments for marking as read
    mocked_post.assert_any_call(
        ANY,  # URL
        headers={'Authorization': ANY, 'Content-Type': 'application/json'},  # Headers
        json={'ids': as_read_ids, 'removeLabelIds': ['UNREAD']}  # JSON data
    )

    # Assert requests.post was called with the correct arguments for marking as unread
    mocked_post.assert_any_call(
        ANY,  # URL
        headers={'Authorization': ANY, 'Content-Type': 'application/json'},  # Headers
        json={'ids': unread_ids, 'addLabelIds': ['UNREAD']}  # JSON data
    )

    # Assert requests.post was called with the correct arguments for moving
    mocked_post.assert_any_call(
        ANY,  # URL
        headers={'Authorization': ANY, 'Content-Type': 'application/json'},  # Headers
        json={'ids': move_ids, 'addLabelIds': ['INBOX']}  # JSON data
    )
    mocked_post.reset_mock()  # Reset the call count before mocking again
    mocked_post.return_value.status_code = 400  # Mock the status code to test the error handling
    modify_api_call(as_read_ids, unread_ids, move_ids)



def test_full_flow(mocker):
    # Mock all external calls: Gmail API, database, and HTTP requests
    mock_gmail_service = Mock()
    mock_db_session = Mock()
    mocker.patch("script.gmail_authenticate", return_value=mock_gmail_service())
    mocker.patch("script.create_db_session", return_value=mock_db_session())
    mocker.patch("script.requests.post", return_value=MockResponse(200, None))
    # Provide a simplified version of load_rules that returns a specific rule
    mocker.patch("script.load_rules", return_value=[{"conditions": [{"field": "From", "predicate": "contains", "value": "example.com"}], "actions": [{"action": "Mark as Read"}]}])

    # Execute main flow
    main()


