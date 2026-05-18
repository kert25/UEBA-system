"""Tests for geo utilities: haversine and coordinate lookup."""

import pytest

from shared.geo_data import get_coordinates, haversine


class TestHaversine:
    """Tests for haversine distance calculation."""

    def test_same_point(self) -> None:
        assert haversine(55.7, 37.6, 55.7, 37.6) == pytest.approx(0, abs=0.01)

    def test_moscow_spb(self) -> None:
        dist = haversine(55.7558, 37.6173, 59.9343, 30.3351)
        assert dist == pytest.approx(635, abs=10)

    def test_moscow_new_york(self) -> None:
        dist = haversine(55.7558, 37.6173, 40.7128, -74.0060)
        assert dist == pytest.approx(7500, abs=100)

    def test_antipodes(self) -> None:
        dist = haversine(0, 0, 0, 180)
        assert dist == pytest.approx(20015, abs=100)

    def test_negative_coords(self) -> None:
        dist = haversine(-33.8, 151.2, -23.5, -46.6)
        assert dist > 0


class TestGetCoordinates:
    """Tests for coordinate lookup."""

    def test_moscow(self) -> None:
        lat, lon = get_coordinates("Russia", "Moscow")
        assert lat == pytest.approx(55.7558, abs=0.001)
        assert lon == pytest.approx(37.6173, abs=0.001)

    def test_unknown_country(self) -> None:
        lat, lon = get_coordinates("Atlantis", "X")
        assert lat == 0.0
        assert lon == 0.0

    def test_known_country_unknown_city(self) -> None:
        lat, lon = get_coordinates("Russia", "Omsk")
        assert lat == 55.7558

    def test_no_city(self) -> None:
        lat, lon = get_coordinates("Japan")
        assert lat == pytest.approx(35.6762, abs=0.001)

    def test_new_york(self) -> None:
        lat, lon = get_coordinates("United States", "New York")
        assert lat == pytest.approx(40.7128, abs=0.001)
