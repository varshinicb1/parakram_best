"""Tests for the corpus ingestion pipeline."""


def test_source_definitions():
    """All source repos have required fields."""
    from corpus.ingest.sources import ALL_SOURCES

    for source in ALL_SOURCES:
        assert source.name, "Source must have a name"
        assert source.url.startswith("https://"), f"Invalid URL: {source.url}"
        assert source.ref, f"Source {source.name} must have a ref/tag"
        assert source.tier in (1, 2, 3), f"Invalid tier: {source.tier}"
        assert source.license, f"Source {source.name} must have a license"


def test_extractor_regex():
    """Function extraction regex matches basic C functions."""
    from corpus.ingest.extractor import FUNC_PATTERN

    test_code = """
void gpio_init(uint8_t pin) {
    GPIO_REG = (1 << pin);
    return;
}

int spi_transfer(uint8_t *buf, size_t len) {
    for (size_t i = 0; i < len; i++) {
        SPI_DR = buf[i];
    }
    return 0;
}
"""
    matches = FUNC_PATTERN.findall(test_code)
    assert len(matches) >= 2, f"Expected 2+ function matches, got {len(matches)}"


def test_tag_inference():
    """Tag inference correctly identifies peripherals."""
    from corpus.ingest.extractor import _infer_tags

    tags = _infer_tags("i2c_read_register", "i2c_master_write_read_device(i2c_port, addr)")
    assert "i2c" in tags

    tags = _infer_tags("spi_init", "SPI_MOSI_PIN = 23; spi_bus_initialize()")
    assert "spi" in tags

    tags = _infer_tags("uart_printf", "USART_SendData(USART1, ch)")
    assert "uart" in tags
