# Third-party assets

The device panel screen renderer bundles two third-party assets. Both are
redistributable under permissive licences, and the full licence text is kept
next to each asset.

## Meteocons weather icons

`custom_components/smhi_odp/panel_icons/` contains a small subset (10 icons)
of [Meteocons](https://github.com/basmilius/weather-icons) by Bas Milius, in
the "fill" style. The PNGs were rasterised from the SVGs kept alongside them.

MIT Licence — see `custom_components/smhi_odp/panel_icons/LICENSE`.

## DejaVu Sans

`custom_components/smhi_odp/fonts/DejaVuSans.ttf` is from the
[DejaVu Fonts](https://dejavu-fonts.github.io/) project. It is bundled rather
than loaded from the host, because a Home Assistant container is not
guaranteed to have any particular font installed.

Bitstream Vera / Arev licences, DejaVu changes in the public domain — see
`custom_components/smhi_odp/fonts/LICENSE`.
