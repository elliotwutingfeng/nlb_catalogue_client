from http import HTTPStatus
from typing import Any, Dict

import httpx
import pytest
from tenacity import wait_none

from nlb_catalogue_client.api.catalogue import get_search_titles
from nlb_catalogue_client.client import AuthenticatedClient
from nlb_catalogue_client.errors import UnexpectedStatus
from nlb_catalogue_client.models.search_titles_response_v2 import SearchTitlesResponseV2


@pytest.fixture()
def client() -> AuthenticatedClient:
    return AuthenticatedClient(base_url="https://api.example.com", token="test_token", raise_on_unexpected_status=True)


@pytest.fixture()
def success_response() -> Dict[str, Any]:
    return {
        "totalRecords": 100,
        "count": 20,
        "hasMoreRecords": True,
        "nextRecordsOffset": 20,
        "titles": [
            {
                "format": {"code": "BK", "name": "BOOK"},
                "brn": 123456,
                "title": "Sample Book Title",
                "author": "John Doe",
                "isbns": ["9781234567890"],
                "publisher": ["Sample Publisher"],
                "publish_date": "2023",
                "language": ["English"],
                "subjects": ["Fiction", "Literature"],
            }
        ],
        "facets": [{"name": "Format", "values": [{"value": "Book", "count": 80}, {"value": "eBook", "count": 20}]}],
    }


@pytest.fixture()
def error_responses() -> Dict[int, Dict[str, Any]]:
    return {
        400: {"error": "Bad Request", "message": "Invalid request parameters", "statusCode": 400},
        401: {"error": "Unauthorized", "message": "Authentication token is invalid", "statusCode": 401},
        404: {"error": "Not Found", "message": "Resource not found", "statusCode": 404},
        405: {"error": "Method Not Allowed", "message": "HTTP method not allowed", "statusCode": 405},
        429: {"error": "Too Many Requests", "message": "Rate limit exceeded", "statusCode": 429},
        500: {"error": "Internal Server Error", "message": "An unexpected error occurred", "statusCode": 500},
        501: {"error": "Not Implemented", "message": "Feature not implemented", "statusCode": 501},
        503: {"error": "Service Unavailable", "message": "Service is temporarily unavailable", "statusCode": 503},
    }


class TestSearchTitles:
    def test_get_kwargs_with_required_params(self):
        kwargs = get_search_titles._get_kwargs(keywords="python programming")

        assert kwargs == {
            "method": "get",
            "url": "/SearchTitles",
            "params": {"Keywords": "python programming", "Limit": 20, "Offset": 0},
        }

    def test_get_kwargs_with_all_params(self):
        kwargs = get_search_titles._get_kwargs(
            keywords="python",
            source="overdrive",
            limit=50,
            sort_fields="title",
            offset=20,
            material_types=["BK", "DVD"],
            intended_audiences=["ADULT", "TEEN"],
            date_from=20230101,
            date_to=20231231,
            locations=["AMKPL", "BIPL"],
            languages=["ENG", "CHI"],
            availability=True,
            fiction=True,
        )

        assert kwargs == {
            "method": "get",
            "url": "/SearchTitles",
            "params": {
                "Keywords": "python",
                "Source": "overdrive",
                "Limit": 50,
                "SortFields": "title",
                "Offset": 20,
                "MaterialTypes": ["BK", "DVD"],
                "IntendedAudiences": ["ADULT", "TEEN"],
                "DateFrom": 20230101,
                "DateTo": 20231231,
                "Locations": ["AMKPL", "BIPL"],
                "Languages": ["ENG", "CHI"],
                "Availability": True,
                "Fiction": True,
            },
        }

    def test_sync_detailed_success(self, mocker, client: AuthenticatedClient, success_response: Dict[str, Any]):
        mock_response = httpx.Response(
            status_code=200,
            json=success_response,
        )
        mocker.patch("httpx.Client.request", return_value=mock_response)

        response = get_search_titles.sync_detailed(client=client, keywords="python")

        assert response.status_code == HTTPStatus.OK
        assert isinstance(response.parsed, SearchTitlesResponseV2)
        assert response.parsed.total_records == 100
        assert response.parsed.count == 20
        assert response.parsed.has_more_records is True
        assert response.parsed.next_records_offset == 20
        assert response.parsed.titles
        assert len(response.parsed.titles) == 1
        assert response.parsed.facets
        assert len(response.parsed.facets) == 1

    def test_sync_success(self, mocker, client: AuthenticatedClient, success_response: Dict[str, Any]):
        mock_response = httpx.Response(
            status_code=200,
            json=success_response,
        )
        mocker.patch("httpx.Client.request", return_value=mock_response)

        response = get_search_titles.sync(client=client, keywords="python")

        assert isinstance(response, SearchTitlesResponseV2)
        assert response.total_records == 100
        assert response.count == 20
        assert response.has_more_records is True
        assert response.next_records_offset == 20
        assert response.titles
        assert len(response.titles) == 1
        assert response.facets
        assert len(response.facets) == 1

    @pytest.mark.asyncio
    async def test_asyncio_success(self, mocker, client: AuthenticatedClient, success_response: Dict[str, Any]):
        mock_response = httpx.Response(
            status_code=200,
            json=success_response,
        )
        mocker.patch("httpx.AsyncClient.request", return_value=mock_response)

        response = await get_search_titles.asyncio(client=client, keywords="python")

        assert isinstance(response, SearchTitlesResponseV2)
        assert response.total_records == 100
        assert response.count == 20
        assert response.has_more_records is True
        assert response.next_records_offset == 20
        assert len(response.titles) == 1
        assert len(response.facets) == 1

    @pytest.mark.parametrize(
        "status_code,error_type",
        [
            (400, "BadRequestError"),
            (401, "UnauthorizedError"),
            (404, "NotFoundError"),
            (405, "MethodNotAllowedError"),
            (429, "TooManyRequestsError"),
            (500, "InternalServerError"),
            (501, "NotImplementedError_"),
            (503, "ServiceUnavailableError"),
        ],
    )
    def test_error_responses_sync(
        self,
        mocker,
        client: AuthenticatedClient,
        error_responses: Dict[int, Dict[str, Any]],
        status_code: int,
        error_type: str,
    ):
        error_mock_response = httpx.Response(
            status_code=status_code,
            json=error_responses[status_code],
        )
        mocker.patch("httpx.Client.request", return_value=error_mock_response)

        # Tenacity to stop waiting
        get_search_titles.sync_detailed.retry.wait = wait_none()

        response = get_search_titles.sync_detailed(client=client, keywords="python")

        assert response.status_code == status_code
        assert error_type in str(type(response.parsed))
        assert response.parsed
        assert not isinstance(response.parsed, SearchTitlesResponseV2)
        assert response.parsed.error == error_responses[status_code]["error"]
        assert response.parsed.message == error_responses[status_code]["message"]
        assert response.parsed.status_code == status_code

    def test_sync_detailed_unexpected_status_raises(
        self,
        mocker,
        client: AuthenticatedClient,
    ):
        unexpected_response = httpx.Response(
            status_code=418,  # I'm a teapot - unexpected status
            json={"error": "Unexpected", "message": "I'm a teapot", "statusCode": 418},
        )
        mocker.patch("httpx.Client.request", return_value=unexpected_response)

        with pytest.raises(UnexpectedStatus):
            get_search_titles.sync_detailed(client=client, keywords="python")

    def test_sync_detailed_unexpected_status_return_none(
        self,
        mocker,
        client: AuthenticatedClient,
    ):
        unexpected_response = httpx.Response(
            status_code=418,  # I'm a teapot - unexpected status
            json={"error": "Unexpected", "message": "I'm a teapot", "statusCode": 418},
        )
        mocker.patch("httpx.Client.request", return_value=unexpected_response)
        client.raise_on_unexpected_status = False

        assert get_search_titles.sync_detailed(client=client, keywords="python").parsed is None
