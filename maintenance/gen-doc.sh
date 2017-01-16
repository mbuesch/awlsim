#!/bin/sh
#
# Generate documentation
#


basedir="$(dirname "$0")"
[ "$(echo "$basedir" | cut -c1)" = '/' ] || basedir="$PWD/$basedir"


die()
{
	echo "$*" >&2
	exit 1
}

gen()
{
	local md="$1"
	local docname="$(basename "$md" .md)"
	local dir="$(dirname "$md")"
	local html="$dir/$docname.html"
	local pdf="$dir/$docname.pdf"

	echo "Generating $docname ..."

	echo "<!DOCTYPE html><html><head><meta http-equiv=\"content-type\" content=\"text/html; charset=utf-8\"></head><body>" > "$html" ||\
		die "Failed to generate"
	markdown "$md" >> "$html" ||\
		die "Failed to generate"
	echo "</body></html>" >> "$html" ||\
		die "Failed to generate"

	wkhtmltopdf "$html" "$pdf" ||\
		die "Failed to generate"
}

for i in "$basedir"/../*.md; do
	gen "$i"
done
