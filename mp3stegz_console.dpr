program mp3stegz_console;

{$APPTYPE CONSOLE}

uses
  SysUtils, uMP3; // uMP3 module by Achmad Zaenuri; e-mail: achmad.zaenuri@gmail.com
begin
  if (ParamStr(1)='hide') then
  begin
        if(HideFile(ParamStr(3),ParamStr(2),ParamStr(4),20)=-1)then WriteLn('Unable to hide: too big/too small');
        WriteLn('Finished');
  end
  else if (ParamStr(1)='reveal') then
  begin
        WriteLn('Revealed into ',RevealFile(ParamStr(2)));
  end
  else if (ParamStr(1)='available') then
  begin
        Halt(uMP3.MaxStegSize(ParamStr(2), 20));
  end
  else
  begin
        WriteLn('mp3stegz by Achmad Zaenuri; Author homepage: http://achmadz.blogspot.com; Author e-mail: achmad.zaenuri@gmail.com');
        WriteLn('mp3stegz hides data in .mp3 audio files.');
        WriteLn('This version was modified for use in console environment. file encryption not included.');
        WriteLn('Usage:');
        WriteLn('mp3stegz_console hide [file] [container mp3] [mp3 with data]');
        WriteLn('mp3stegz_console reveal [mp3 with data]');
  end;
end.
