FROM python:3.12-slim

# LibreOffice renders the slide preview, the poppler tools turn its PDF into PNG.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libreoffice-impress \
        poppler-utils \
        fonts-dejavu-core \
        fontconfig \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
# The templates ask for Poppins. Without the bundled faces LibreOffice substitutes another
# font, and the preview then shows something the measurement never planned for.
RUN cp src/outline2pptx/fonts/poppins/*.ttf /usr/local/share/fonts/ \
    && fc-cache -f
RUN pip install --no-cache-dir ".[ui]" \
    && useradd --create-home --uid 1000 app \
    && mkdir -p /data && chown app:app /data

USER app
EXPOSE 8000
VOLUME ["/data"]

# The web UI: a topic or an outline in the browser, a PowerPoint file back.
# Settings come from OUTLINE2PPTX_* environment variables, for example OUTLINE2PPTX_BASE_URL
# and OUTLINE2PPTX_MODEL, or from the fields on the page.
CMD ["outline2pptx", "serve", "--host", "0.0.0.0", "--port", "8000"]
