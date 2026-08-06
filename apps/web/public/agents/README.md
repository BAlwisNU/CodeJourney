# Agent artwork

Drop the character images here and they appear on the landing page's coach
tabs. Until they exist the tabs render a monogram placeholder instead, so the
section is never broken -- it just looks plainer.

Expected files (any of .png / .webp / .jpg -- update ART in
src/components/AgentTabs.tsx if you use a different extension):

    all.png       the four of them together, for the "Meet all four" tab
    scout.png     one character, chest up
    coach.png
    forge.png
    keeper.png

Portraits look best square-ish and cropped to head and shoulders; the group
shot is shown wide. Keep them under ~300KB each -- they are on the landing
page, whose whole promise is that it opens instantly.
